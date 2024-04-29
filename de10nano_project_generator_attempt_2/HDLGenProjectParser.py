from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from typing import List, Tuple
from HDLGenDataType import *

@dataclass
class PathBuilder:
    _path: str

    def __post_init__(self):
        self.path = self._path

    @property
    def path(self) -> str:
        return self._path
    
    @path.setter
    def path(self, value)-> None:
        if not isinstance(value, str):
            raise ValueError(f'Expect a str, but {value} ia a {type(value)}')
        path = Path(value).resolve()
        self._path = path.as_posix()

@dataclass
class HDLGenProjectParser:
    _path: str

    def __post_init__(self):
        self.path = self._path

    @property
    def path(self) -> str:
        return self._path
    
    @path.setter
    def path(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f'Expect a string but {value} is a {type(value)}')
        path_builder = PathBuilder(value)
        self._path = path_builder.path()

    def parser(self) -> Tuple[str, str, str, List[Port], str]:
        '''
        Parameters:
        None

        Returns:
        project_name (str): the name of the project.
        top_hdl_path (str): the path of top module's hdl file
        environment_path (str): the path of the project environment
        ports (List[Port]): the ports of user's design
        testbench (str): test bench
        '''
        with open(self.path, 'r') as file:
            xml_string = file.read()

        root = ET.fromstring(xml_string)
        
        project_name = self._design_name_parser(root)
        top_hdl_path = self._top_level_hdl_parser(root)
        environment_path = self._environment_path_parser(root)
        ports = self._signals_parser(root)
        testbench = self._testbench_parser(root)

        return project_name, top_hdl_path, environment_path, ports, testbench
    
    def _design_name_parser(root: Element) -> str:
        return root.find('.//projectManager/settings/name').text
    
    def _top_level_hdl_parser(root: Element) -> str:
        design_name = root.find('.//projectManager/settings/name').text
        location = root.find('.//projectManager/settings/location').text
        sub_folders = root.find('.//genFolder/vhdl_folder')
        hdl_path: Path
        for folder in sub_folders:
            folder_path = folder.text
            path = Path(folder_path)
            if path.is_dir() and path.name.lower() == 'model':
                hdl_path = path
        if hdl_path:
            hdl_path = location / hdl_path / f'{design_name}.vhd'
            hdl_path = hdl_path.as_posix()
            return hdl_path
        else:
            raise ValueError('Did not found a HDL path')

    def _environment_path_parser(root: Element) -> str:
        path_string = root.find('.//projectManager/setting/environment').text
        path = Path(path_string).as_posix()
        return path
    
    def _signals_parser(root: Element) -> List[Port]:
        ports: List[Port] = []
        signals = root.findall('.//entityIOPorts/signal')
        for signal in signals:
            name = signal.find('name').text
            mode = signal.find('mode').text
            type = signal.find('type').text
            ports.append(Port(name, mode, type))
        return ports
    
    def _testbench_parser(root: Element) -> str:
        return root.find('.//testbench/TBNode').text
    
@dataclass
class HDLGenEnvironmentParser:
    _path: str

    def __post_init__(self):
        self.path = self._path

    @property
    def path(self) -> str:
        return self._path
    
    @path.setter
    def path(self, value) -> None:
        path = Path(value)
        if not path.exists():
            raise ValueError(f'Path {value} not exist.')
        self._path = value

    def parser(self) -> List[str]:
        with open(self.path, 'r') as file:
            xml_string = file.read()

        root = ET.fromstring(xml_string)
        sub_model_strings = root.findall('.//hdlDesign/components/conponent')

        paths: List[str] = []
        path_prefix = Path(self.path)

        for string in sub_model_strings:
            sub_model_path = Path(string.find('dir').text)
            if not sub_model_path.is_absolute():
                path = path_prefix.joinpath(sub_model_path)
            else:
                path = sub_model_path
            if path.exists():
                paths.append(path.as_posix())
            else:
                print(f'Warning: {path} not exists')

        return paths