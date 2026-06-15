#!/usr/bin/env python3
"""
neural_viz_node.py
==================
Subscribes to /neural_state and publishes a MarkerArray for RViz2
so you can watch all 299 neurons light up in real time above the worm.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Pose
import json, os, math
from ament_index_python.packages import get_package_share_directory


class NeuralVizNode(Node):
    def __init__(self):
        super().__init__('neural_viz_node')

        pkg = get_package_share_directory('celegans_sim')
        with open(os.path.join(pkg, 'resource', 'connectome.json')) as f:
            data = json.load(f)

        self.neuron_names = data['neurons']
        self.N = len(self.neuron_names)

        # Lay neurons out in a sphere above the worm
        self.positions = []
        for i in range(self.N):
            phi   = math.acos(1 - 2 * (i + 0.5) / self.N)
            theta = math.pi * (1 + 5**0.5) * i
            r = 0.4
            self.positions.append((
                r * math.sin(phi) * math.cos(theta),
                r * math.sin(phi) * math.sin(theta),
                r * math.cos(phi) + 0.6   # float above worm
            ))

        # Class colors: sensory=green, motor=orange, inter=blue
        ndata = data['neuron_data']
        self.colors = []
        for n in self.neuron_names:
            nd = ndata.get(n, {})
            if nd.get('sensory'):
                self.colors.append((0.4, 0.9, 0.5))   # green
            elif any(n.startswith(x) for x in ['DB','DD','VB','VD','DA','VA']):
                self.colors.append((0.95, 0.6, 0.2))  # orange
            else:
                self.colors.append((0.4, 0.6, 0.95))  # blue

        self.activations = [0.0] * self.N
        self.worm_x = 0.0
        self.worm_y = 0.0

        self.create_subscription(Float32MultiArray, '/neural_state',  self.neural_cb, 10)
        self.create_subscription(Pose,              '/worm/pose',     self.pose_cb,   10)
        self.pub = self.create_publisher(MarkerArray, '/neural_markers', 10)
        self.create_timer(0.1, self.publish_markers)  # 10 Hz
        self.get_logger().info('Neural visualizer ready — watch /neural_markers in RViz2')

    def neural_cb(self, msg):
        if len(msg.data) == self.N:
            self.activations = list(msg.data)

    def pose_cb(self, msg):
        self.worm_x = msg.position.x
        self.worm_y = msg.position.y

    def publish_markers(self):
        ma = MarkerArray()
        for i in range(self.N):
            m = Marker()
            m.header.frame_id = 'world'
            m.header.stamp = self.get_clock().now().to_msg()
            m.ns = 'neurons'
            m.id = i
            m.type = Marker.SPHERE
            m.action = Marker.ADD

            px, py, pz = self.positions[i]
            m.pose.position.x = self.worm_x + px
            m.pose.position.y = self.worm_y + py
            m.pose.position.z = pz
            m.pose.orientation.w = 1.0

            act = self.activations[i]
            scale = 0.012 + act * 0.035
            m.scale.x = m.scale.y = m.scale.z = scale

            r, g, b = self.colors[i]
            m.color.r = r
            m.color.g = g
            m.color.b = b
            m.color.a = 0.25 + act * 0.75

            m.lifetime.sec = 0
            m.lifetime.nanosec = 200_000_000  # 200 ms timeout
            ma.markers.append(m)

        self.pub.publish(ma)


def main(args=None):
    rclpy.init(args=args)
    node = NeuralVizNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
