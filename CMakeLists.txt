cmake_minimum_required(VERSION 3.5)
PROJECT(ChimeraTK-Chai NONE)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/Modules)

set(${PROJECT_NAME}_MAJOR_VERSION 01)
set(${PROJECT_NAME}_MINOR_VERSION 00)
set(${PROJECT_NAME}_PATCH_VERSION 01)
include(cmake/set_version_numbers.cmake)

find_package(Python 3 REQUIRED COMPONENTS Interpreter)

# install Python modules to correct platform-dependent directory (if installing to system prefix)
if("${CMAKE_INSTALL_PREFIX}" STREQUAL "/usr" OR "${CMAKE_INSTALL_PREFIX}" STREQUAL "/usr/local")
  set(python_install_path ${Python_SITEARCH})
else()
  set(python_install_path "lib/python${Python_VERSION_MAJOR}.${Python_VERSION_MINOR}/site-packages")
endif()

#dragon_inject_dependency(textual)
#dragon_inject_dependency(ChimeraTK-DeviceAccess-PythonBindings)

# install programs and python modules
install(PROGRAMS ${PROJECT_SOURCE_DIR}/Chai.py DESTINATION bin RENAME chai)
install(DIRECTORY ${PROJECT_SOURCE_DIR}/chai DESTINATION "${python_install_path}")
