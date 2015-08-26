"""
Python interface to CUBLAS functions.
"""

import ctypes as ct
from quagga.cuda import cudart


_libcublas = ct.cdll.LoadLibrary('libcublas.so')


ct_cublas_handle = ct.c_void_p
ct_cublas_status = ct.c_int


cublas_statuses = {
    1: 'CUBLAS_STATUS_NOT_INITIALIZED',
    3: 'CUBLAS_STATUS_ALLOC_FAILED',
    7: 'CUBLAS_STATUS_INVALID_VALUE',
    8: 'CUBLAS_STATUS_ARCH_MISMATCH',
    11: 'CUBLAS_STATUS_MAPPING_ERROR',
    13: 'CUBLAS_STATUS_EXECUTION_FAILED',
    14: 'CUBLAS_STATUS_INTERNAL_ERROR',
    15: 'CUBLAS_STATUS_NOT_SUPPORTED',
    16: 'CUBLAS_STATUS_LICENSE_ERROR'
}


class CublasError(Exception):
    """CUBLAS error."""
    pass


cublas_exceptions = {}
for cublas_error_code, cublas_status_name in cublas_statuses.iteritems():
    class_name = cublas_status_name.replace('_STATUS_', '_')
    class_name = ''.join(each.capitalize() for each in class_name.split('_'))
    klass = type(class_name, (CublasError, ), {'__doc__': cublas_status_name})
    cublas_exceptions[cublas_error_code] = klass


def check_cublas_status(status):
    if status != 0:
        try:
            raise cublas_exceptions[status]
        except KeyError:
            raise CublasError('unknown CUBLAS error {}'.format(status))


_libcublas.cublasCreate_v2.restype = ct_cublas_status
_libcublas.cublasCreate_v2.argtypes = [ct.POINTER(ct_cublas_handle)]
def cublas_create(handle):
    status = _libcublas.cublasCreate_v2(ct.byref(handle))
    check_cublas_status(status)


_libcublas.cublasDestroy_v2.restype = ct_cublas_status
_libcublas.cublasDestroy_v2.argtypes = [ct_cublas_handle]
def cublas_destroy(handle):
    status = _libcublas.cublasDestroy_v2(handle)
    check_cublas_status(status)


_libcublas.cublasGetVersion_v2.restype = ct_cublas_status
_libcublas.cublasGetVersion_v2.argtypes = [ct_cublas_handle, ct.c_void_p]
def cublas_get_version(handle):
    version = ct.c_int()
    status = _libcublas.cublasGetVersion_v2(handle, ct.byref(version))
    check_cublas_status(status)
    return version.value


_libcublas.cublasSetStream_v2.restype = ct_cublas_status
_libcublas.cublasSetStream_v2.argtypes = [ct_cublas_handle, cudart.ct_cuda_stream]
def cublas_set_stream(handle, stream):
    status = _libcublas.cublasSetStream_v2(handle, stream)
    check_cublas_status(status)


_libcublas.cublasGetStream_v2.restype = ct_cublas_status
_libcublas.cublasGetStream_v2.argtypes = [ct_cublas_handle, ct.POINTER(cudart.ct_cuda_stream)]
def cublas_get_stream(handle, stream):
    status = _libcublas.cublasGetStream_v2(handle, ct.byref(stream))
    check_cublas_status(status)



cublas_pointer_mode = {
    'host': 0,
    'device': 1
}


_libcublas.cublasGetPointerMode_v2.restype = ct_cublas_status
_libcublas.cublasGetPointerMode_v2.argtypes = [ct_cublas_handle,
                                               ct.POINTER(ct.c_int)]
def cublas_get_pointer_mode(handle):
    pointer_mode = ct.c_int()
    status = _libcublas.cublasGetPointerMode_v2(handle, ct.byref(pointer_mode))
    check_cublas_status(status)
    for name in cublas_pointer_mode:
        if cublas_pointer_mode[name] == pointer_mode:
            return name


_libcublas.cublasSetPointerMode_v2.restype = ct_cublas_status
_libcublas.cublasSetPointerMode_v2.argtypes = [ct_cublas_handle,
                                               ct.c_int]
def cublas_set_pointer_mode(handle, pointer_mode):
    status = _libcublas.cublasSetPointerMode_v2(handle, cublas_pointer_mode[pointer_mode])
    check_cublas_status(status)


_libcublas.cublasSetVector.restype = ct_cublas_status
_libcublas.cublasSetVector.argtypes = [ct.c_int, ct.c_int, ct.c_void_p,
                                       ct.c_int, ct.c_void_p, ct.c_int]
def cublas_set_vector(n, elem_size, host_ptr, incx, device_ptr, incy):
    status = _libcublas.cublasSetVector(n, elem_size, host_ptr, incx, device_ptr, incy)
    check_cublas_status(status)


_libcublas.cublasSetVectorAsync.restype = ct_cublas_status
_libcublas.cublasSetVectorAsync.argtypes = [ct.c_int, ct.c_int,
                                            ct.c_void_p, ct.c_int,
                                            ct.c_void_p, ct.c_int,
                                            cudart.ct_cuda_stream]
def cublas_set_vector_async(n, elem_size, host_ptr, incx, device_ptr, incy, stream):
    status = _libcublas.cublasSetVectorAsync(n, elem_size, host_ptr, incx, device_ptr, incy, stream)
    check_cublas_status(status)


_libcublas.cublasGetVector.restype = ct_cublas_status
_libcublas.cublasGetVector.argtypes = [ct.c_int, ct.c_int,
                                       ct.c_void_p, ct.c_int,
                                       ct.c_void_p, ct.c_int]
def cublas_get_vector(n, elem_size, device_ptr, incx, host_ptr, incy):
    status = _libcublas.cublasGetVector(n, elem_size, device_ptr, incx, host_ptr, incy)
    check_cublas_status(status)


_libcublas.cublasGetVectorAsync.restype = ct_cublas_status
_libcublas.cublasGetVectorAsync.argtypes = [ct.c_int, ct.c_int,
                                            ct.c_void_p, ct.c_int,
                                            ct.c_void_p, ct.c_int,
                                            cudart.ct_cuda_stream]
def cublas_get_vector_async(n, elem_size, device_ptr, incx, host_ptr, incy, stream):
    status = _libcublas.cublasGetVectorAsync(n, elem_size, device_ptr, incx, host_ptr, incy, stream)
    check_cublas_status(status)


_libcublas.cublasSscal_v2.restype = ct_cublas_status
_libcublas.cublasSscal_v2.argtypes = [ct_cublas_handle, ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int]
def cublas_s_scal(handle, n, alpha, x, incx):
    status = _libcublas.cublasSscal_v2(handle, n, ct.byref(alpha), x, incx)
    check_cublas_status(status)


_libcublas.cublasSaxpy_v2.restype = ct_cublas_status
_libcublas.cublasSaxpy_v2.argtypes = [ct_cublas_handle, ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.c_int]

def cublas_s_axpy(handle, n, alpha, x, incx, y, incy):
    status = _libcublas.cublasSaxpy_v2(handle, n, ct.byref(alpha), x, incx, y, incy)
    check_cublas_status(status)


_libcublas.cublasScopy_v2.restype = ct_cublas_status
_libcublas.cublasScopy_v2.argtypes = [ct_cublas_handle,
                                   ct.c_int,
                                   ct.POINTER(ct.c_float),
                                   ct.c_int,
                                   ct.POINTER(ct.c_float),
                                   ct.c_int]
def cublas_s_copy(handle, n, x, incx, y, incy):
    status = _libcublas.cublasScopy_v2(handle, n, x, incx, y, incy)
    check_cublas_status(status)


_libcublas.cublasSdot_v2.restype = ct_cublas_status
_libcublas.cublasSdot_v2.argtypes = [ct_cublas_handle,
                                     ct.c_int,
                                     ct.POINTER(ct.c_float),
                                     ct.c_int,
                                     ct.POINTER(ct.c_float),
                                     ct.c_int,
                                     ct.POINTER(ct.c_float)]
def cublas_s_dot(handle, n, x, incx, y, incy, result):
    status = _libcublas.cublasSdot_v2(handle, n, x, incx, y, incy, ct.byref(result))
    check_cublas_status(status)


cublas_op = {
    'n': 0,  # CUBLAS_OP_N
    'N': 0,
    't': 1,  # CUBLAS_OP_T
    'T': 1,
    'c': 2,  # CUBLAS_OP_C
    'C': 2,
}


_libcublas.cublasSgemv_v2.restype = ct_cublas_status
_libcublas.cublasSgemv_v2.argtypes = [ct_cublas_handle,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int]
def cublas_s_gemv(handle, trans, m, n, alpha, a, lda, x, incx, beta, y, incy):
    status = _libcublas.cublasSgemv_v2(handle, cublas_op[trans], m, n, ct.byref(alpha), a, lda, x, incx, ct.byref(beta), y, incy)
    check_cublas_status(status)


_libcublas.cublasSgemm_v2.restype = ct_cublas_status
_libcublas.cublasSgemm_v2.argtypes = [ct_cublas_handle,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.c_int,
                                      ct.POINTER(ct.c_float),
                                      ct.POINTER(ct.c_float),
                                      ct.c_int]
def cublas_s_gemm(handle, transa, transb, m, n, k, alpha, a, lda, b, ldb, beta, c, ldc):
    status = _libcublas.cublasSgemm_v2(handle, cublas_op[transa], cublas_op[transb], m, n, k, ct.byref(alpha), a, lda, b, ldb, ct.byref(beta), c, ldc)
    check_cublas_status(status)
