# Install script for directory: /mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/src/aerothon_slam_grid

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_install/aerothon_slam_grid")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so"
         RPATH "")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/libaerothon_slam_grid.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so")
    file(RPATH_CHANGE
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so"
         OLD_RPATH "/opt/ros/jazzy/lib:"
         NEW_RPATH "")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libaerothon_slam_grid.so")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ament_index/resource_index/package_run_dependencies" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_index/share/ament_index/resource_index/package_run_dependencies/aerothon_slam_grid")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ament_index/resource_index/parent_prefix_path" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_index/share/ament_index/resource_index/parent_prefix_path/aerothon_slam_grid")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid/environment" TYPE FILE FILES "/opt/ros/jazzy/share/ament_cmake_core/cmake/environment_hooks/environment/ament_prefix_path.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid/environment" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/ament_prefix_path.dsv")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid/environment" TYPE FILE FILES "/opt/ros/jazzy/share/ament_cmake_core/cmake/environment_hooks/environment/path.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid/environment" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/path.dsv")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/local_setup.bash")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/local_setup.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/local_setup.zsh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/local_setup.dsv")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_environment_hooks/package.dsv")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ament_index/resource_index/packages" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_index/share/ament_index/resource_index/packages/aerothon_slam_grid")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid/cmake" TYPE FILE FILES
    "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_core/aerothon_slam_gridConfig.cmake"
    "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/ament_cmake_core/aerothon_slam_gridConfig-version.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/aerothon_slam_grid" TYPE FILE FILES "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/src/aerothon_slam_grid/package.xml")
endif()

if(CMAKE_INSTALL_COMPONENT)
  set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
file(WRITE "/mnt/d/MY DOCUMENTS/VIT/Team Rotor Fpv/AEROTHON/.scratch/lidar_boot_20261017/colcon_build/aerothon_slam_grid/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
