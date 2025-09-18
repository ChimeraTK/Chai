import numpy as np
import deviceaccess as da


def get_raw_numpy_type(raw_type):
    conversion = {
        "none": None, "int8": np.int8, "uint8": np.uint8, "int16": np.int16,
        "uint16": np.uint16, "int32": np.int32, "uint32": np.uint32, "int64": np.int64,
        "uint64": np.uint64, "float32": np.float32, "float64": np.float64, "string": str,
        "Boolean": bool, "Void": "void", "unknown": "unknown"}
    return conversion[raw_type.getAsString()]


def build_data_type_string(data_desriptor) -> str:
    type_string = str(data_desriptor.fundamentalType())
    if data_desriptor.fundamentalType() == da.FundamentalType.numeric:
        type_string = "unsigned"
        if data_desriptor.isSigned():
            type_string = "signed "
        if data_desriptor.isIntegral():
            type_string += " integer"
        else:
            type_string += " fractional"
    return type_string.title()


class AccessorHolder:
    def __init__(self, accessor: da.GeneralRegisterAccessor, info: da.pb.RegisterInfo,
                 dummyWriteAccessor: da.GeneralRegisterAccessor | None):
        self.accessor = accessor
        self.dummyWriteAccessor = dummyWriteAccessor
        self.info = info
    accessor: da.GeneralRegisterAccessor
    dummyWriteAccessor: da.GeneralRegisterAccessor | None
    info: da.pb.RegisterInfo
