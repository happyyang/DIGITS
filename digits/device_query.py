#!/usr/bin/env python
# Copyright (c) 2014-2015, NVIDIA CORPORATION.  All rights reserved.

import ctypes
import platform

class c_cudaDeviceProp(ctypes.Structure):
    """
    Passed to cudart.cudaGetDeviceProperties()
    """
    _fields_ = [
            ('name', ctypes.c_char * 256),
            ('totalGlobalMem', ctypes.c_size_t),
            ('sharedMemPerBlock', ctypes.c_size_t),
            ('regsPerBlock', ctypes.c_int),
            ('warpSize', ctypes.c_int),
            ('memPitch', ctypes.c_size_t),
            ('maxThreadsPerBlock', ctypes.c_int),
            ('maxThreadsDim', ctypes.c_int * 3),
            ('maxGridSize', ctypes.c_int * 3),
            ('clockRate', ctypes.c_int),
            ('totalConstMem', ctypes.c_size_t),
            ('major', ctypes.c_int),
            ('minor', ctypes.c_int),
            ('textureAlignment', ctypes.c_size_t),
            ('texturePitchAlignment', ctypes.c_size_t),
            ('deviceOverlap', ctypes.c_int),
            ('multiProcessorCount', ctypes.c_int),
            ('kernelExecTimeoutEnabled', ctypes.c_int),
            ('integrated', ctypes.c_int),
            ('canMapHostMemory', ctypes.c_int),
            ('computeMode', ctypes.c_int),
            ('maxTexture1D', ctypes.c_int),
            ('maxTexture1DMipmap', ctypes.c_int),
            ('maxTexture1DLinear', ctypes.c_int),
            ('maxTexture2D', ctypes.c_int * 2),
            ('maxTexture2DMipmap', ctypes.c_int * 2),
            ('maxTexture2DLinear', ctypes.c_int * 3),
            ('maxTexture2DGather', ctypes.c_int * 2),
            ('maxTexture3D', ctypes.c_int * 3),
            ('maxTexture3DAlt', ctypes.c_int * 3),
            ('maxTextureCubemap', ctypes.c_int),
            ('maxTexture1DLayered', ctypes.c_int * 2),
            ('maxTexture2DLayered', ctypes.c_int * 3),
            ('maxTextureCubemapLayered', ctypes.c_int * 2),
            ('maxSurface1D', ctypes.c_int),
            ('maxSurface2D', ctypes.c_int * 2),
            ('maxSurface3D', ctypes.c_int * 3),
            ('maxSurface1DLayered', ctypes.c_int * 2),
            ('maxSurface2DLayered', ctypes.c_int * 3),
            ('maxSurfaceCubemap', ctypes.c_int),
            ('maxSurfaceCubemapLayered', ctypes.c_int * 2),
            ('surfaceAlignment', ctypes.c_size_t),
            ('concurrentKernels', ctypes.c_int),
            ('ECCEnabled', ctypes.c_int),
            ('pciBusID', ctypes.c_int),
            ('pciDeviceID', ctypes.c_int),
            ('pciDomainID', ctypes.c_int),
            ('tccDriver', ctypes.c_int),
            ('asyncEngineCount', ctypes.c_int),
            ('unifiedAddressing', ctypes.c_int),
            ('memoryClockRate', ctypes.c_int),
            ('memoryBusWidth', ctypes.c_int),
            ('l2CacheSize', ctypes.c_int),
            ('maxThreadsPerMultiProcessor', ctypes.c_int),
            ('streamPrioritiesSupported', ctypes.c_int),
            ('globalL1CacheSupported', ctypes.c_int),
            ('localL1CacheSupported', ctypes.c_int),
            ('sharedMemPerMultiprocessor', ctypes.c_size_t),
            ('regsPerMultiprocessor', ctypes.c_int),
            ('managedMemSupported', ctypes.c_int),
            ('isMultiGpuBoard', ctypes.c_int),
            ('multiGpuBoardGroupID', ctypes.c_int),
            # added later with cudart.cudaDeviceGetPCIBusId
            # (needed by NVML)
            ('pciBusID_str', ctypes.c_char * 13),
            ]

class struct_c_nvmlDevice_t(ctypes.Structure):
    """
    Handle to a device in NVML
    """
    pass # opaque handle
c_nvmlDevice_t = ctypes.POINTER(struct_c_nvmlDevice_t)

class c_nvmlUtilization_t(ctypes.Structure):
    """
    Passed to nvml.nvmlDeviceGetUtilizationRates()
    """
    _fields_ = [
            ('gpu', ctypes.c_uint),
            ('memory', ctypes.c_uint),
            ]

def get_library(name):
    """
    Returns a ctypes.CDLL or None
    """
    try:
        if platform.system() == 'Linux':
            return ctypes.cdll.LoadLibrary('%s.so' % name)
        elif platform.system() == 'Darwin':
            return ctypes.cdll.LoadLibrary('%s.dylib' % name)
    except OSError as e:
        #print 'ERROR in device_query.get_library("%s"): %s' % (name, e.message)
        pass
    return None

devices = None

def get_devices():
    """
    Returns a list of c_cudaDeviceProp's
    Prints an error and returns None if something goes wrong
    """
    global devices
    if devices is not None:
        # Only query CUDA once
        return devices
    devices = []

    cudart = get_library('libcudart')
    if cudart is None:
        return []

    # check CUDA version
    cuda_version = ctypes.c_int()
    rc = cudart.cudaRuntimeGetVersion(ctypes.byref(cuda_version))
    if rc != 0:
        print 'cudaRuntimeGetVersion() failed with error #%s' % rc
        return []
    if cuda_version.value < 6050:
        print 'ERROR: Cuda version must be >= 6.5, not "%s"' % cuda_version.value
        return []

    # get number of devices
    num_devices = ctypes.c_int()
    cudart.cudaGetDeviceCount(ctypes.byref(num_devices))

    # query devices
    for x in xrange(num_devices.value):
        properties = c_cudaDeviceProp()
        rc = cudart.cudaGetDeviceProperties(ctypes.byref(properties), x)
        if rc == 0:
            pciBusID_str = ' ' * 13
            # also save the string representation of the PCI bus ID
            rc = cudart.cudaDeviceGetPCIBusId(ctypes.c_char_p(pciBusID_str), 13, x)
            if rc == 0:
                properties.pciBusID_str = pciBusID_str
            devices.append(properties)
        del properties
    return devices

def get_device(device_id):
    """
    Returns a c_cudaDeviceProp
    """
    return get_devices()[int(device_id)]

def get_utilization(device_id):
    """
    Returns a c_nvmlUtilization_t for the given device
    """
    device = get_device(device_id)
    if device is None:
        return None

    nvml = get_library('libnvidia-ml')
    if nvml is None:
        return None

    rc = nvml.nvmlInit()
    if rc != 0:
        raise RuntimeError('nvmlInit() failed with error #%s' % rc)

    try:
        # get device handle
        handle = c_nvmlDevice_t()
        rc = nvml.nvmlDeviceGetHandleByPciBusId(ctypes.c_char_p(device.pciBusID_str), ctypes.byref(handle))
        if rc != 0:
            raise RuntimeError('nvmlDeviceGetHandleByIndex() failed with error #%s' % rc)

        utilization = c_nvmlUtilization_t()
        rc = nvml.nvmlDeviceGetUtilizationRates(handle, ctypes.byref(utilization))
        if rc != 0:
            if rc == 3:
                # not supported for this device
                return None
            raise RuntimeError('nvmlDeviceGetUtilizationRates() failed with error #%s' % rc)
        return utilization
    finally:
        rc = nvml.nvmlShutdown()


if __name__ == '__main__':
    if not len(get_devices()):
        print 'No devices found.'
    for i, device in enumerate(get_devices()):
        print 'Device #%d: %s' % (i, device.name)
        for name, t in device._fields_:
            # Don't print int arrays
            if t in [ctypes.c_char, ctypes.c_int, ctypes.c_size_t]:
                print '%30s %s' % (name, getattr(device, name))
        u = get_utilization(i)
        if u is not None:
            print '%30s %s%% (NVML)' % ('GPU utilization', u.gpu)
            print '%30s %s%% (NVML)' % ('Memory utilization', u.memory)
        print

