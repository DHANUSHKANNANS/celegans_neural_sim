#!/usr/bin/env python3
"""
worm_body_node.py
=================
Translates muscle activations from neural_sim_node into joint commands
for the worm URDF in Gazebo. Also reads contact sensors and publishes
back as /sensory_input to close the loop.

Subscribes:
  /muscle_activation  (std_msgs/Float32MultiArray)
  /worm_behavior      (std_msgs/String)

Publishes:
  /worm/joint_states  (sensor_msgs/JointState)
  /sensory_input      (std_msgs/Float32MultiArray)
  /worm/pose          (geometry_msgs/Pose)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, String
from sensor_msgs.msg import JointState
from geometry_msgs.msg import Pose, Twist
import numpy as np
import math


NUM_SEGMENTS = 12

# Joint limits (radians) — C. elegans bends ~60 deg max
MAX_BEND = 0.8


class WormBodyNode(Node):
    def __init__(self):
        super().__init__('worm_body_node')

        # Current muscle activations
        self.muscles = np.zeros(NUM_SEGMENTS * 2, dtype=np.float32)
        self.behavior = 'IDLE'

        # Worm body state
        self.joint_angles = np.zeros(NUM_SEGMENTS - 1, dtype=np.float64)
        self.head_pos = np.array([0.0, 0.0, 0.05])  # x, y, z in world frame
        self.heading  = 0.0   # yaw in radians
        self.speed    = 0.0
        self.step_count = 0

        # Simulated contact sensors
        self.head_contact  = 0.0
        self.tail_contact  = 0.0
        self.food_distance = 5.0  # distance to nearest food

        # Subscribers
        self.create_subscription(Float32MultiArray, '/muscle_activation',
                                 self.muscle_callback, 10)
        self.create_subscription(String, '/worm_behavior',
                                 self.behavior_callback, 10)

        # Publishers
        self.pub_joints   = self.create_publisher(JointState,          '/worm/joint_states', 10)
        self.pub_sensory  = self.create_publisher(Float32MultiArray,   '/sensory_input',     10)
        self.pub_pose     = self.create_publisher(Pose,                '/worm/pose',         10)
        self.pub_cmd_vel  = self.create_publisher(Twist,               '/worm/cmd_vel',      10)

        # 50 Hz body update
        self.create_timer(0.02, self.update)
        self.get_logger().info('Worm body node ready — 12 segments, 11 joints')

    def muscle_callback(self, msg: Float32MultiArray):
        if len(msg.data) >= NUM_SEGMENTS * 2:
            self.muscles = np.array(msg.data[:NUM_SEGMENTS * 2], dtype=np.float32)

    def behavior_callback(self, msg: String):
        self.behavior = msg.data.split('|')[0]

    def update(self):
        self.step_count += 1

        # ── Compute joint angles from muscle differential ────────
        for i in range(NUM_SEGMENTS - 1):
            dorsal  = float(self.muscles[i * 2])
            ventral = float(self.muscles[i * 2 + 1])
            # Differential contraction bends the body
            diff = dorsal - ventral
            # Low-pass filter for smooth motion
            self.joint_angles[i] += (diff * MAX_BEND - self.joint_angles[i]) * 0.3

        # ── Derive locomotion from body wave ─────────────────────
        fwd_muscle  = float(np.mean(self.muscles[0::2]))   # avg dorsal
        rev_muscle  = float(np.mean(self.muscles[1::2]))   # avg ventral

        if self.behavior == 'REVERSING':
            self.speed = -0.015
        elif self.behavior == 'IDLE':
            self.speed =  0.005
        else:
            wave_amp = float(np.std(self.muscles))
            self.speed = wave_amp * 0.08

        # Head turn from first joint angle
        turn_rate = float(self.joint_angles[0]) * 0.04
        self.heading += turn_rate

        # Move head position
        self.head_pos[0] += math.cos(self.heading) * self.speed
        self.head_pos[1] += math.sin(self.heading) * self.speed

        # Boundary bounce (arena ±5 m)
        for ax in [0, 1]:
            if abs(self.head_pos[ax]) > 4.5:
                self.head_pos[ax] = np.clip(self.head_pos[ax], -4.5, 4.5)
                self.heading += math.pi + (np.random.random() - 0.5) * 0.5
                self.head_contact = 0.9  # trigger nociception

        # Decay contacts
        self.head_contact = max(0.0, self.head_contact - 0.05)
        self.tail_contact = max(0.0, self.tail_contact - 0.05)

        # Simulate food gradient (food at origin)
        dist = math.sqrt(self.head_pos[0]**2 + self.head_pos[1]**2)
        self.food_distance = dist
        food_signal = max(0.0, 1.0 - dist / 5.0)

        # ── Publish joint states ──────────────────────────────────
        js = JointState()
        js.header.stamp = self.get_clock().now().to_msg()
        js.name = [f'joint_{i}' for i in range(NUM_SEGMENTS - 1)]
        js.position = self.joint_angles.tolist()
        js.velocity = [0.0] * (NUM_SEGMENTS - 1)
        self.pub_joints.publish(js)

        # ── Publish sensory feedback → neural sim ─────────────────
        s = Float32MultiArray()
        s.data = [
            float(self.head_contact),   # [0] head touch
            float(self.tail_contact),   # [1] tail touch
            float(food_signal),          # [2] food proximity
            float(self.head_contact > 0.7),  # [3] nociception
            0.0,                         # [4] temperature (placeholder)
        ]
        self.pub_sensory.publish(s)

        # ── Publish pose ──────────────────────────────────────────
        pose = Pose()
        pose.position.x = float(self.head_pos[0])
        pose.position.y = float(self.head_pos[1])
        pose.position.z = float(self.head_pos[2])
        self.pub_pose.publish(pose)

        # ── Publish cmd_vel for Gazebo model ─────────────────────
        twist = Twist()
        twist.linear.x  = float(self.speed)
        twist.angular.z = float(turn_rate)
        self.pub_cmd_vel.publish(twist)

        # Log every 5 s
        if self.step_count % 250 == 0:
            self.get_logger().info(
                f'State: {self.behavior} | pos=({self.head_pos[0]:.2f}, {self.head_pos[1]:.2f}) '
                f'| speed={self.speed:.4f} | food_dist={self.food_distance:.2f}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = WormBodyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
