# C. elegans Autonomous ROS2 Simulation

Real connectome-driven autonomous worm simulation using:
- **299 neurons, 3,363 synapses** from OpenWorm / Varshney et al. dataset
- **Leaky Integrate-and-Fire** neural model at 100 Hz
- **Gazebo** physics simulation with agar plate environment
- **RViz2** neural activity visualization

---

## Package Structure

```
celegans_sim/
├── celegans_sim/
│   ├── neural_sim_node.py   ← The connectome brain (100 Hz LIF)
│   ├── worm_body_node.py    ← Joint controller + sensory feedback
│   └── neural_viz_node.py   ← RViz2 neuron markers
├── urdf/
│   └── celegans.urdf        ← 12-segment articulated worm body
├── worlds/
│   └── agar_plate.world     ← Gazebo world (petri dish + food)
├── launch/
│   └── celegans_sim.launch.py
├── resource/
│   └── connectome.json      ← Real connectome data
├── package.xml
├── CMakeLists.txt
└── setup.py
```

---

## Installation

### 1. Copy package into your ROS2 workspace

```bash
cp -r celegans_sim ~/ros2_ws/src/
cd ~/ros2_ws
```

### 2. Install Python dependencies

```bash
pip3 install numpy
```

### 3. Build

```bash
cd ~/ros2_ws
colcon build --packages-select celegans_sim
source install/setup.bash
```

---

## Running

### Full simulation (Gazebo + RViz2)

```bash
source ~/ros2_ws/install/setup.bash
ros2 launch celegans_sim celegans_sim.launch.py
```

### Neural sim only (no Gazebo, for testing)

```bash
ros2 launch celegans_sim celegans_sim.launch.py use_gazebo:=false use_rviz:=false
```

### Watch topics in real time

```bash
# Current behavior state
ros2 topic echo /worm_behavior

# All 299 neuron activations (10 Hz)
ros2 topic echo /neural_state

# Muscle activation (24 values)
ros2 topic echo /muscle_activation

# Worm position
ros2 topic echo /worm/pose
```

### Manually fire a sensory stimulus

```bash
# Simulate head touch → triggers ALML/ALMR → reversal
ros2 topic pub --once /sensory_input std_msgs/Float32MultiArray \
  "data: [1.0, 0.0, 0.0, 0.0, 0.0]"

# Simulate food smell → AWA fires → forward locomotion
ros2 topic pub --once /sensory_input std_msgs/Float32MultiArray \
  "data: [0.0, 0.0, 0.9, 0.0, 0.0]"

# Simulate nociception (pain) → ASH → reversal
ros2 topic pub --once /sensory_input std_msgs/Float32MultiArray \
  "data: [0.0, 0.0, 0.0, 1.0, 0.0]"
```

---

## ROS2 Topics

| Topic | Type | Description |
|---|---|---|
| `/sensory_input` | Float32MultiArray | [head_touch, tail_touch, food, nociception, temperature] |
| `/muscle_activation` | Float32MultiArray | 24 values: dorsal+ventral per segment |
| `/neural_state` | Float32MultiArray | All 299 neuron activations |
| `/worm_behavior` | String | Current behavior label |
| `/worm/joint_states` | JointState | 11 joint angles |
| `/worm/pose` | Pose | Head position in world |
| `/neural_markers` | MarkerArray | RViz2 neuron spheres |

---

## Neural Circuits

The simulation uses real neural circuits from the connectome:

| Stimulus | Sensory Neurons | Circuit | Behavior |
|---|---|---|---|
| Food smell | AWA, AWB | AWA → AIY → AVBL/AVBR | Forward locomotion |
| Head touch | ALML, ALMR | ALML → AVD → AVAL/AVAR | Reversal |
| Tail touch | PLML, PLMR | PLML → PVC → AVBL | Forward acceleration |
| Nociception | ASH | ASH → AVA → DA/VA motors | Reverse + turn |
| Temperature | AFD | AFD → AIY → locomotion | Thermotaxis |

---

## Data Source

Connectome data from:
> Varshney LR, Chen BL, Paniagua E, Hall DH, Chklovskii DB (2011).
> *Structural Properties of the Caenorhabditis elegans Neuronal Network.*
> PLoS Comput Biol 7(2): e1001066.

Available via [OpenWorm](http://openworm.org) project.
