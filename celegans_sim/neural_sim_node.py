#!/usr/bin/env python3
"""
neural_sim_node.py
==================
The brain of C. elegans — runs the real connectome (299 neurons, 3363 synapses)
using a Leaky Integrate-and-Fire model at 100 Hz.

Subscribes:
  /sensory_input  (std_msgs/Float32MultiArray)  — sensory activations from Gazebo

Publishes:
  /muscle_activation  (std_msgs/Float32MultiArray)  — 24 muscle group values
  /neural_state       (std_msgs/Float32MultiArray)  — all 299 neuron activations (for viz)
  /worm_behavior      (std_msgs/String)              — current behavior state label
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, String
import numpy as np
import json
import os
from ament_index_python.packages import get_package_share_directory


# ── Leaky Integrate-and-Fire constants ────────────────────────────
DECAY         = 0.94      # membrane potential decay per step
THRESHOLD     = 0.35      # fire threshold
SYNAPSE_SCALE = 0.035     # weight scaling
REFRACTORY    = 3         # steps of refractory period after firing
NUM_SEGMENTS  = 12        # body segments → muscle groups
NUM_MUSCLES   = NUM_SEGMENTS * 2  # dorsal + ventral per segment


class NeuralSimNode(Node):
    def __init__(self):
        super().__init__('neural_sim_node')
        self.get_logger().info('Loading C. elegans connectome...')

        # ── Load connectome ────────────────────────────────────────
        pkg_dir = get_package_share_directory('celegans_sim')
        data_path = os.path.join(pkg_dir, 'resource', 'connectome.json')
        with open(data_path, 'r') as f:
            data = json.load(f)

        self.neuron_names = data['neurons']           # list of 299 names
        self.N = len(self.neuron_names)
        self.key = data['key']                        # named neuron indices
        self.dorsal_motors = data['dorsal']           # DB/DD motor neuron indices
        self.ventral_motors = data['ventral']         # VB/VD motor neuron indices

        # Build adjacency as arrays for fast numpy ops
        edges = data['edges']                         # [from, to, is_gap, weight]
        self.edge_from   = np.array([e[0] for e in edges], dtype=np.int32)
        self.edge_to     = np.array([e[1] for e in edges], dtype=np.int32)
        self.edge_weight = np.array([e[3] for e in edges], dtype=np.float32) * SYNAPSE_SCALE

        # ── Neural state ───────────────────────────────────────────
        self.V          = np.zeros(self.N, dtype=np.float32)  # membrane potential
        self.refrac     = np.zeros(self.N, dtype=np.int32)    # refractory counter
        self.fired_last = np.zeros(self.N, dtype=np.bool_)

        # ── Autonomous drive timers ────────────────────────────────
        self.step_count = 0
        self.behavior_state = 'EXPLORING'
        self.reverse_timer  = 0

        # ── Publishers ────────────────────────────────────────────
        self.pub_muscle   = self.create_publisher(Float32MultiArray, '/muscle_activation', 10)
        self.pub_neural   = self.create_publisher(Float32MultiArray, '/neural_state',      10)
        self.pub_behavior = self.create_publisher(String,            '/worm_behavior',     10)

        # ── Subscriber ────────────────────────────────────────────
        self.create_subscription(Float32MultiArray, '/sensory_input',
                                 self.sensory_callback, 10)

        # ── 100 Hz timer ──────────────────────────────────────────
        self.create_timer(0.01, self.step)
        self.get_logger().info(f'Neural sim ready: {self.N} neurons, {len(edges)} synapses')

    # ──────────────────────────────────────────────────────────────
    def sensory_callback(self, msg: Float32MultiArray):
        """Inject sensory signals from Gazebo into the neural circuit."""
        d = msg.data
        # d[0] = head touch, d[1] = tail touch, d[2] = food proximity,
        # d[3] = nociception, d[4] = temperature
        if len(d) >= 5:
            if d[0] > 0.3:   self._fire(self.key['alml'], d[0] * 0.8)   # head touch L
            if d[0] > 0.3:   self._fire(self.key['almr'], d[0] * 0.8)   # head touch R
            if d[1] > 0.3:   self._fire(self.key['plml'], d[1] * 0.8)   # tail touch L
            if d[1] > 0.3:   self._fire(self.key['plmr'], d[1] * 0.8)   # tail touch R
            if d[2] > 0.1:   self._fire(self.key['awa'],  d[2] * 0.6)   # food/olfaction
            if d[3] > 0.5:   self._fire(self.key['ash'],  d[3] * 0.9)   # nociception
            if d[4] > 0.3:   self._fire(self.key['afd'],  d[4] * 0.5)   # temperature

    # ──────────────────────────────────────────────────────────────
    def _fire(self, idx: int, strength: float = 0.8):
        """Inject activation into a specific neuron."""
        if 0 <= idx < self.N:
            self.V[idx] = min(1.0, self.V[idx] + strength)

    # ──────────────────────────────────────────────────────────────
    def step(self):
        """Main neural simulation step (100 Hz)."""
        self.step_count += 1

        # ── Autonomous spontaneous activity ───────────────────────
        self._autonomous_drive()

        # ── Integrate-and-Fire step ───────────────────────────────
        # Neurons in refractory period can't fire
        can_fire = self.refrac == 0

        # Who fires this step?
        fired = can_fire & (self.V >= THRESHOLD)
        self.fired_last = fired

        # Propagate spikes via connectome
        if np.any(fired):
            firing_indices = np.where(fired)[0]
            for fi in firing_indices:
                # Find all outgoing edges from this neuron
                mask = self.edge_from == fi
                targets = self.edge_to[mask]
                weights = self.edge_weight[mask]
                np.add.at(self.V, targets, weights)
                self.V = np.clip(self.V, 0.0, 1.0)
            # Set refractory
            self.refrac[fired] = REFRACTORY

        # Decay membrane potentials
        self.V *= DECAY
        self.V[self.V < 0.001] = 0.0

        # Count down refractory
        self.refrac = np.maximum(0, self.refrac - 1)

        # ── Compute muscle outputs ─────────────────────────────────
        muscles = self._compute_muscle_activation()

        # ── Publish ───────────────────────────────────────────────
        # Muscle activation (24 values: 12 dorsal + 12 ventral)
        m_msg = Float32MultiArray()
        m_msg.data = muscles.tolist()
        self.pub_muscle.publish(m_msg)

        # Full neural state (every 10 steps = 10 Hz for viz)
        if self.step_count % 10 == 0:
            n_msg = Float32MultiArray()
            n_msg.data = self.V.tolist()
            self.pub_neural.publish(n_msg)

            # Behavior label
            b_msg = String()
            fwd = self.V[self.key['fwdL']] + self.V[self.key['fwdR']]
            rev = self.V[self.key['revL']] + self.V[self.key['revR']]
            noci = self.V[self.key['ash']]
            food = self.V[self.key['awa']]
            if noci > 0.5:
                b_msg.data = 'NOCICEPTION|ASH firing → reversal circuit active'
            elif rev > fwd * 1.2:
                b_msg.data = 'REVERSING|AVA/AVAR driving backward locomotion'
            elif food > 0.3:
                b_msg.data = 'FOOD_SENSING|AWA chemosensory → AIY → forward'
            elif fwd > 0.2:
                b_msg.data = 'FORWARD|AVBL/AVBR driving forward locomotion'
            else:
                b_msg.data = 'IDLE|Tonic spontaneous activity'
            self.pub_behavior.publish(b_msg)

    # ──────────────────────────────────────────────────────────────
    def _autonomous_drive(self):
        """
        Inject biologically realistic spontaneous activity.
        Real C. elegans has tonic excitation of command neurons.
        """
        # Tonic forward drive (AVB neurons always slightly active)
        if self.step_count % 15 == 0:
            self._fire(self.key['fwdL'], 0.25)
            self._fire(self.key['fwdR'], 0.25)

        # Head oscillation via RIM/AIB (every ~0.5 s = 50 steps)
        if self.step_count % 50 == 0:
            self._fire(self.key['rim'], 0.4)

        # Spontaneous turns via AIB
        if self.step_count % 200 == 0:
            self._fire(self.key['aib'], 0.5)

        # Random brief reverse (AVA burst, every ~5 s)
        if self.step_count % 500 == 0:
            self._fire(self.key['revL'], 0.7)
            self._fire(self.key['revR'], 0.7)
            self._fire(self.key['revD'], 0.5)

    # ──────────────────────────────────────────────────────────────
    def _compute_muscle_activation(self) -> np.ndarray:
        """
        Map motor neuron activations to 24 muscle values.
        C. elegans locomotion: sinusoidal wave driven by DB/VB (fwd) and DA/VA (rev).
        Returns: [d0,v0, d1,v1, ..., d11,v11] — dorsal/ventral per segment
        """
        muscles = np.zeros(NUM_MUSCLES, dtype=np.float32)

        fwd_drive = float(self.V[self.key['fwdL']] + self.V[self.key['fwdR']]) * 0.5
        rev_drive = float(self.V[self.key['revL']] + self.V[self.key['revR']] + self.V[self.key['revD']]) / 3.0
        head_turn = float(self.V[self.key['rim']] + self.V[self.key['aib']]) * 0.5

        # Phase from step count → sinusoidal body wave
        phase = self.step_count * 0.08  # ~1.3 Hz body wave

        for seg in range(NUM_SEGMENTS):
            seg_phase = phase - seg * 0.55  # wave propagates head to tail

            # Forward locomotion: alternating dorsal/ventral activation
            fwd_dorsal  = max(0.0,  np.sin(seg_phase)) * fwd_drive
            fwd_ventral = max(0.0, -np.sin(seg_phase)) * fwd_drive

            # Reverse locomotion: wave goes tail to head
            rev_dorsal  = max(0.0,  np.sin(-seg_phase + seg * 1.1)) * rev_drive
            rev_ventral = max(0.0, -np.sin(-seg_phase + seg * 1.1)) * rev_drive

            # Head turn bias (first 2 segments)
            turn_bias = head_turn * 0.4 if seg < 2 else 0.0

            muscles[seg * 2]     = float(np.clip(fwd_dorsal  + rev_dorsal  + turn_bias, 0, 1))
            muscles[seg * 2 + 1] = float(np.clip(fwd_ventral + rev_ventral,             0, 1))

        return muscles


def main(args=None):
    rclpy.init(args=args)
    node = NeuralSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
