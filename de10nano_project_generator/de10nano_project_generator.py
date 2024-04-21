# Log
import logging
import sys
# re
import re
# Type
from typing import List, Tuple
# XML
from xml.dom import minidom
# path
from pathlib import Path
# signals
from signals import *
# tcl & hdl scripts
from HDL_n_Tcl import *
# commandline
import argparse

# globel setting
E_CLK : str = 'e_clk'           # 标准外部时钟的名称（外部时钟指的是 de10nano 通过编程的方式从 PIO 向 FPGA 发送的时钟信号）
E_CLK_EN : str = 'e_clk_en'     # 标准外部时钟enable的名称

# log
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.INFO)
file_hander = logging.FileHandler('de10nano_project_generator.log')
stream_hander = logging.StreamHandler() # print to the console
file_hander.setLevel(logging.DEBUG)
stream_hander.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
file_hander.setFormatter(formatter)
stream_hander.setFormatter(formatter)
module_logger.addHandler(file_hander)
module_logger.addHandler(stream_hander)

def hdlgen_environment_parser(hdlgen_project_path: str) -> List[str]:
    """
    This function parses the HDLGen environment information to extract the VHDL file paths.

    Parameters:
    HDLGen_project_path (str): The path to the HDLGen project file.

    Returns:
    vhdl_file_paths (List[str]): A list containing the paths of all VHDL files extracted from the project.
    Raises:
    FileNotFoundError: If the provided HDLGen project file does not exist.
    AttributeError: If the XML structure does not contain the expected nodes.
    """

    module_logger.info(f'INFO: Parsing HDLGen environment at {hdlgen_project_path}')
    
    # Convert input path to Path object and ensure it exists
    hdlgen_project_path_obj = Path(hdlgen_project_path)
    if not hdlgen_project_path_obj.exists():
        module_logger.error(f'ERROR: The HDLGen project file "{hdlgen_project_path}" does not exist.')
        raise FileNotFoundError(f'The file "{hdlgen_project_path}" does not exist.')

    hdlgen_project_path_obj = hdlgen_project_path_obj.resolve()

    # Load the HDLGen project XML
    try:
        project = minidom.parse(str(hdlgen_project_path_obj))
    except Exception as e:
        module_logger.error(f'ERROR: Unable to parse the XML file due to {e}')
        raise

    # Extract package folder location and resolve it to an absolute path
    try:
        project_env = project.getElementsByTagName("environment")[0]
        main_package_hdlgen_path = Path(project_env.firstChild.data).resolve() / 'Package/mainPackage.hdlgen'
        
        # Parse mainPackage.hdlgen for component paths
        main_package = minidom.parse(str(main_package_hdlgen_path))
        components = main_package.getElementsByTagName("component")
        vhdl_file_paths = []

        if components:
            for component in components:
                dir_tag = component.getElementsByTagName('dir')[0]
                vhdl_path = main_package_hdlgen_path.parent / dir_tag.firstChild.data
                vhdl_file_paths.append(str(vhdl_path.absolute()))

        # Get the top module VHDL file path
        project_name = project.getElementsByTagName("name")[0].firstChild.data
        top_module_vhdl_path = (Path(project.getElementsByTagName('location')[0].firstChild.data).resolve() / f'VHDL/model/{project_name}.vhd').absolute()
        vhdl_file_paths.append(str(top_module_vhdl_path))

        # Get the MainPackage.vhd path
        main_package_vhd_path = Path(project_env.firstChild.data).resolve() / 'Package/MainPackage.vhd'
        vhdl_file_paths.append(str(main_package_vhd_path.absolute()))
        
        return vhdl_file_paths

    except IndexError as ie:
        module_logger.error(f'ERROR: Unable to parse the XML due to missing expected nodes: {ie}')
        raise AttributeError('The XML structure does not contain the expected nodes.')

    except Exception as e:
        module_logger.error(f'ERROR: Unexpected error occurred while parsing the XML: {e}')
        raise

def hdlgen_project_parser(hdlgen_project_path: str) -> Tuple[List[Port], List[str], str, str]:
    '''
    This function aims to get the information from the hdlgen project file, which is organised in XML.

    Parameters:
    - hdlgen_project_path (str): The path of the hdlgen project file, which is expected as an absolute path. Relative path will work if you use this program in the command line.

    Returns:
    - top_module_ports (List[Port]): The ports of the user's design.
    - hdl_paths (List[str]): The paths of the hdl file of the top module and submodules, returned in absolute path.
    - design_name (str): The name of the top module.
    - testbench (str): The testbench of the top module.
    '''
    module_logger.info(f'INFO: Function hdlgen_project_parser started with parameter ---- hdlgen_project_path: {hdlgen_project_path}.')
    top_module_ports: List[Port] = []
    hdl_paths: List[str] = []
    design_name: str = ""
    testbench: str = ""

    project_path = Path(hdlgen_project_path)

    # Check if the path exists
    if not project_path.exists():
        module_logger.error(f'ERROR: path {hdlgen_project_path} not exist.')
        raise FileNotFoundError(f'File not found: {hdlgen_project_path}')

    if project_path.is_absolute():
        module_logger.info('INFO: Received an absolute path.')
    else:
        project_path = project_path.absolute()
        module_logger.info('INFO: Received a relative path. Converting to absolute path.')
    project_path = project_path.as_posix()  # Transfer path to posix path

    try:
        project = minidom.parse(project_path)
        design_name = project.getElementsByTagName('name')[0].firstChild.data

        # Process entityIOPorts
        entity_ioports = project.getElementsByTagName("entityIOPorts")[0]
        if entity_ioports is None:
            module_logger.error('ERROR: No entityIOPorts found in the XML.')
            raise ValueError('Invalid XML structure. Missing entityIOPorts.')

        for signal in entity_ioports.getElementsByTagName("signal"):
            if signal.getElementsByTagName("name") == []:
                module_logger.warning('WARNING: Signal without a name found. Skipping...')
                continue
            
            name = signal.getElementsByTagName("name")[0].firstChild.data
            if name == 'clk':
                module_logger.info('INFO: clk detected. Skipping...')
                continue
            
            try:
                mode = signal.getElementsByTagName("mode")[0].firstChild.data
                type_str = signal.getElementsByTagName("type")[0].firstChild.data
                description = signal.getElementsByTagName("description")[0].firstChild.data
            except IndexError:
                module_logger.error('ERROR: Incomplete signal data in XML. Skipping...')
                continue

            port = Port(name, mode, type_str, description)
            module_logger.info(f"INFO: signal name: {port.name}, signal mode: {port.mode}, signal type: {port.type_str}, signal width: {port.width}")
            top_module_ports.append(port)

        testbench_element = project.getElementsByTagName('TBNote')
        if testbench_element:
            testbench = testbench_element[0].firstChild.data
        else:
            module_logger.warning('WARNING: No TBNote element found in the XML. Testbench will be empty.')

        # TODO: Parse and extract hdl_paths and testbench from the XML

    except Exception as e:
        module_logger.error(f'ERROR: An error occurred while parsing the XML: {e}')
        raise

    return top_module_ports, hdl_paths, design_name, testbench

def qsys_pios_allocator(top_module_ports : list) -> List[Tuple[Port, PIO, int, int]]:
    connections : List[Tuple[Port, PIO, int, int]]
    pios : List[PIO]

    '''
    This function is to connect the ports of user's design to PIOs that generated by qsys
    '''

    return connections, pios

def project_tcl_generator(hdl_paths : List[str], output_directory : str) -> None:
    pass

def top_module_generator(
        connections : List[Tuple[Port, PIO, int, int]],
        output_directory : str,
        design_name : str) -> None:
    pass

def qsys_tcl_generator(pios : List[PIO], output_directory : str) -> None:
    pass

def project_directory_generator(output_directory : str) -> None:
    pass

def xml_file_generator(output_directory : str, design_name : str, testbench : str) -> None:
    pass

def bat_file_generator(
        output_directory : str,
        quartus_path : str,
        qsys_script_path : str,
        qsys_generate_path : str,
        quartus_cpf_path : str) -> None:
    pass

def de10nano_project_generator(
    hdlgen_project_path: str,
    output_directory: str,
    quartus_path: str,
    qsys_script_path: str,
    qsys_generate_path: str,
    quartus_cpf_path: str
) -> None:
    """
    This function automates the generation of a Quartus project and the obtainment of a programmable file.
    It creates a batch file; running it will automatically generate the Quartus project and the programmable file.

    Parameters:
    - hdlgen_project_path (str): Absolute or relative path to the hdlgen project (use absolute when integrating with HDLGen).
    - output_directory (str): Directory where you want to place the Quartus project.
    - quartus_path (str): Absolute path to the quartus.exe.
    - qsys_script_path (str): Absolute path to the qsys_script.exe.
    - qsys_generate_path (str): Absolute path to the qsys_generate.exe.
    - quartus_cpf_path (str): Absolute path to the quartus_cpf.exe.

    Step-by-step process:
    1. Parse the hdlgen project file to get:
       - top module ports
       - paths to HDL files
       - design name
       - testbench
    2. Connect ports to PIOs using qsys_pios_allocator().
    3. Create the folder structure for the Quartus project and scripts in `output_directory`.
    4. Generate the TCL script for the Quartus project that adds HDL files.
    5. Generate the top module file based on connection information.
    6. Generate the QSYS TCL script to create PIOS.
    7. Generate an XML file containing user's design info for the de10nano.
    8. Finally, generate a batch file to execute the automated project generation steps.
    """

    top_module_ports: List[Port]
    pios: List[PIO]
    connections: List[Tuple[Port, PIO, int, int]]
    hdl_paths: List[str]
    design_name: str
    testbench: str

    # Parse hdlgen project to extract necessary info
    top_module_ports, hdl_paths, design_name, testbench = hdlgen_project_parser(hdlgen_project_path)

    # Allocate and connect PIOs to ports
    connections, pios = qsys_pios_allocator(top_module_ports)

    # Prepare directories and files for Quartus project
    project_directory_generator(output_directory)

    # Generate the TCL script for adding HDL files to the project
    project_tcl_generator(hdl_paths, output_directory)

    # Generate the top module file with connection details
    top_module_generator(connections, output_directory, design_name)

    # Generate QSYS TCL script for creating PIOS
    qsys_tcl_generator(pios, output_directory)

    # Generate XML file with design and testbench info for de10nano
    xml_file_generator(output_directory, design_name, testbench)

    # Generate the batch file to automate project generation
    bat_file_generator(
        output_directory,
        quartus_path,
        qsys_script_path,
        qsys_generate_path,
        quartus_cpf_path
    )

    
def main():
    parser = argparse.ArgumentParser(description="DE10Nano Project Generator")
    parser.add_argument('-p', '--path', help='Path to the hdlgen project')
    args = parser.parse_args()
    de10nano_project_generator(args.path, ' ', ' ', ' ', ' ', ' ')


if __name__ == '__main__':
    main()