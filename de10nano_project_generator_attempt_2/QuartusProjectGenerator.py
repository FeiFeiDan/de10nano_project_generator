from dataclasses import dataclass
from HDL_n_Tcl import *
from HDLGenDataType import PIO, Port
from HDLGenProjectParser import HDLGenProjectParser, HDLGenEnvironmentParser

@dataclass
class Quartus:
    quartus_path: str
    qsys_script_path: str
    qsys_generate_path: str
    quartus_cpf_path: str
    output_directory: str

@dataclass
class QuartusProjectGenerator:
    pass