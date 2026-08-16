"""Mission 2 bring-up: MAVROS + perception + avoidance + SLAM + RViz + GCS aggregator + video.

Examples:
  # SITL + Gazebo (image/scan from sim bridge, launch RViz and SLAM):
  ros2 launch mission_bringup mission2.launch.py use_sim:=true rviz:=true slam:=true

  # Real hardware:
  ros2 launch mission_bringup mission2.launch.py use_sim:=false \
       fcu_url:=/dev/ttyAMA0:921600 image_topic:=/image_raw rviz:=false
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, Command
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim = LaunchConfiguration('use_sim')
    fcu_url = LaunchConfiguration('fcu_url')
    image_topic = LaunchConfiguration('image_topic')
    scan_topic = LaunchConfiguration('scan_topic')
    target = LaunchConfiguration('target')
    launch_rviz = LaunchConfiguration('rviz')
    launch_slam = LaunchConfiguration('slam')

    pkg_bringup = get_package_share_directory('mission_bringup')
    rviz_config_file = os.path.join(pkg_bringup, 'config', 'aerothon_slam.rviz')

    # URDF Robot description for RViz & TF
    pkg_desc = get_package_share_directory('uav_description')
    xacro_file = os.path.join(pkg_desc, 'urdf', 'uav.urdf.xacro')
    robot_description = ParameterValue(Command(['xacro "', xacro_file, '"']), value_type=str)

    args = [
        DeclareLaunchArgument('use_sim', default_value='true', description='Use sim time (Gazebo)'),
        DeclareLaunchArgument('fcu_url', default_value='udp://127.0.0.1:14555@127.0.0.1:14556', description='MAVROS FCU URL (via MAVLink router)'),
        DeclareLaunchArgument('image_topic', default_value='/image_raw', description='Camera image topic'),
        DeclareLaunchArgument('scan_topic', default_value='/scan', description='LaserScan topic'),
        DeclareLaunchArgument('target', default_value='', description='Pre-assigned target QR (empty=dynamic)'),
        DeclareLaunchArgument('rviz', default_value='true', description='Launch RViz 2 with SLAM/TF displays'),
        DeclareLaunchArgument('slam', default_value='true', description='Launch async slam_toolbox 2D SLAM node'),
    ]

    # 1. Robot State Publisher (publishes TF tree and robot_description)
    rsp_node = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': use_sim}],
    )

    # 2. MAVROS Core Node
    mavros = Node(
        package='mavros', executable='mavros_node', output='screen',
        parameters=[{'fcu_url': fcu_url, 'gcs_url': '',
                     'target_system_id': 1, 'target_component_id': 1,
                     'use_sim_time': use_sim}],
    )

    # 3. Computer Vision Perception Nodes
    qr = Node(
        package='perception_qr', executable='qr_node', output='screen',
        parameters=[{'image_topic': image_topic, 'target': target,
                     'use_sim_time': use_sim}],
    )

    banner = Node(
        package='perception_banner', executable='banner_node', output='screen',
        parameters=[{'image_topic': image_topic, 'use_sim_time': use_sim}],
    )

    redzone = Node(
        package='perception_redzone', executable='redzone_node', output='screen',
        parameters=[{'image_topic': image_topic, 'use_sim_time': use_sim}],
    )

    # 4. Reactive Obstacle Avoidance Controller
    controller = Node(
        package='avoidance', executable='velocity_controller', output='screen',
        parameters=[{'scan_topic': scan_topic, 'use_sim_time': use_sim}],
    )

    # 5. Autonomous Behavior Tree Mission Executive
    mission = Node(
        package='mission_bt', executable='mission_tree', output='screen',
        parameters=[{'use_sim_time': use_sim}],
    )

    # 6. GCS Aggregator WebSocket Server (port 8765)
    readiness = Node(
        package='gcs_aggregator', executable='readiness', output='screen',
        parameters=[{'use_sim_time': use_sim, 'image_topic': image_topic}],
    )

    aggregator = Node(
        package='gcs_aggregator', executable='aggregator', output='screen',
        parameters=[{'use_sim_time': use_sim}],
    )

    # 7. Annotated MJPEG Video Stream Server (port 8080)
    video = Node(
        package='web_video_server', executable='web_video_server', output='screen',
        parameters=[{'port': 8080, 'use_sim_time': use_sim}],
    )

    # 8. slam_toolbox (Online 2D SLAM Mapping)
    slam_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim,
            'odom_frame': 'odom',
            'map_frame': 'map',
            'base_frame': 'base_link',
            'scan_topic': scan_topic,
            'mode': 'mapping',
            'resolution': 0.05,
            'max_laser_range': 12.0,
            'minimum_time_interval': 0.1,
            'transform_timeout': 0.2,
            'tf_buffer_duration': 30.0,
        }],
        condition=IfCondition(launch_slam),
    )

    # slam_toolbox is a lifecycle node. Without this manager it remains
    # inactive, so RViz receives LaserScan data but never receives /map.
    slam_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_slam',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim,
            'autostart': True,
            'node_names': ['slam_toolbox'],
            'bond_timeout': 0.0,
        }],
        condition=IfCondition(launch_slam),
    )

    # 9. RViz 2 Visualizer with SLAM, costmap, point cloud, camera view
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim}],
        # Mesa 25 on this Wayland session mis-links RViz's indexed map shader
        # on the Intel Vulkan-backed path. Software GL is stable for RViz and
        # does not affect Gazebo, which remains hardware rendered separately.
        additional_env={
            'LIBGL_ALWAYS_SOFTWARE': '1',
            'QT_OPENGL': 'software',
        },
        output='screen',
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription(args + [
        rsp_node, mavros, qr, banner, redzone,
        controller, mission, readiness, aggregator, video,
        # The Gazebo odometry bridge needs a few seconds to establish odom TF.
        # Activating slam_toolbox before that point leaves its initial scan
        # filter without transforms and delays the first map indefinitely.
        TimerAction(period=8.0, actions=[slam_node, slam_lifecycle_manager]),
        rviz_node
    ])
