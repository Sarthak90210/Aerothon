# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_aerothon_slam_grid_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED aerothon_slam_grid_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(aerothon_slam_grid_FOUND FALSE)
  elseif(NOT aerothon_slam_grid_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(aerothon_slam_grid_FOUND FALSE)
  endif()
  return()
endif()
set(_aerothon_slam_grid_CONFIG_INCLUDED TRUE)

# output package information
if(NOT aerothon_slam_grid_FIND_QUIETLY)
  message(STATUS "Found aerothon_slam_grid: 0.1.0 (${aerothon_slam_grid_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'aerothon_slam_grid' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT aerothon_slam_grid_DEPRECATED_QUIET)
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(aerothon_slam_grid_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${aerothon_slam_grid_DIR}/${_extra}")
endforeach()
