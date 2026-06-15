"""
celegans_sim.launch.py  —  ROS2 Jazzy + Gazebo Harmonic
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg = get_package_share_directory('celegans_sim')

    use_rviz_arg   = DeclareLaunchArgument('use_rviz',   default_value='true')
    use_gazebo_arg = DeclareLaunchArgument('use_gazebo', default_value='true')
    use_rviz   = LaunchConfiguration('use_rviz')
    use_gazebo = LaunchConfiguration('use_gazebo')

    urdf_file  = os.path.join(pkg, 'urdf',   'celegans.urdf')
    world_file = os.path.join(pkg, 'worlds', 'agar_plate.world')

    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # ── Gazebo Harmonic (ROS2 Jazzy default) ──────────────────────
    # Jazzy uses "gz sim" not "gazebo"
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_file],
        output='screen',
        condition=IfCondition(use_gazebo)
    )

    # ── gz_ros_bridge: bridge GZ topics ↔ ROS2 topics ────────────
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen',
        condition=IfCondition(use_gazebo)
    )

    # ── Robot state publisher ─────────────────────────────────────
    robot_state_pub = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}]
    )

    # ── Spawn worm into Gazebo (delayed 4 s) ─────────────────────
    spawn_worm = TimerAction(
        period=4.0,
        actions=[Node(
            package='ros_gz_sim',
            executable='create',
            name='spawn_celegans',
            arguments=[
                '-name',  'celegans',
                '-topic', 'robot_description',
                '-x', '0.0', '-y', '0.0', '-z', '0.05'
            ],
            output='screen',
            condition=IfCondition(use_gazebo)
        )]
    )

    # ── Neural sim node (the connectome brain) ───────────────────
    neural_sim = Node(
        package='celegans_sim',
        executable='neural_sim_node',
        name='neural_sim_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # ── Worm body controller ──────────────────────────────────────
    worm_body = Node(
        package='celegans_sim',
        executable='worm_body_node',
        name='worm_body_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # ── Neural visualizer ─────────────────────────────────────────
    neural_viz = Node(
        package='celegans_sim',
        executable='neural_viz_node',
        name='neural_viz_node',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # ── RViz2 ─────────────────────────────────────────────────────
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz)
    )

 # Joint state publisher — broadcasts all segment TFs
    joint_state_pub = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}]
    )

    return LaunchDescription([
        use_rviz_arg, use_gazebo_arg,
        gazebo,
        gz_bridge,
        robot_state_pub,
        joint_state_pub,
        spawn_worm,
        neural_sim,
        worm_body,
        neural_viz,
        rviz2,
    ])
