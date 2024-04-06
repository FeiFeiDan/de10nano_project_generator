'''
de10nano_project_generator module written by Chenyang LIU
E-mail: c.liu7@universityofgalway.ie
This module is to 

LOG: if this value is True, the log will printed in the console. if you don't want those logs bother you, you can set it as False

de10nano_project_generator(): this function is the most primary function

The rest of the function is the private function.
'''





from xml.dom import minidom
import re
from HDL_n_Tcl import *
import os
import subprocess





LOG = True





class Pio:
    def __init__(self, name, mode, address):
        self.mode = mode
        self.available_bit = 63 # Means the highest available bit, when the pio is full, this value should be -1
        self.pio_name = name
        self.export_name = name + '_export'
        self.address = address

    def connect(self, width):
        assert self.available_bit+1 >= width, "ERROR: Available bits is not enough."
        self.available_bit -= width





class Port:
    def __init__(self, name, mode, type_str, description):
        self.name = name
        self.mode = mode
        self.type_str = type_str
        self.description = description
        self.width = self.get_width(type_str)

    def get_width(self, type_str):
        match = re.match(r'(?:single bit|bus\(\s*(\d+)\s*downto\s*(\d+)\s*\))', type_str)
        if match:
            if match.group(0) == 'single bit':
                return 1
            else:
                start, end = map(int, match.groups())
                if start > end:
                    return start - end + 1
                else:
                    raise ValueError(f'ERROR: Higher bit is small than Lower bit')
        else:
            assert False, f"ERROR: Signal type is not supported yet: {type_str}"





def mode_convert(mode):
    '''
    This function is for helping compare the direction of port and parallel IO, since the the direaction of your design and the parallel IO is opposite
    '''
    if mode == 'out':
        return 'in'
    elif mode == 'in':
        return 'out'
    else:
        assert False, 'ERROR: mode is not supported'





def print_log(str):
    '''
    Set the LOG for False, you will not see the 'INFO' in the console
    '''
    if LOG:
        print(str)





def generate_project_tcl(HDLGen_project_path, output_path = ''):
    '''
    The generate_project_tcl function creates a TCL script for adding VHDL files to a Quartus project from an HDLGen project file. It extracts component paths from mainPackage.hdlgen, constructs TCL commands, and includes the top module and MainPackage.vhd. The script is saved to a specified location.

    Parameters:

    HDLGen_project_path: Path to the HDLGen project file.
    output_path (optional): Directory to save the generated TCL script. Defaults to the current directory if not specified.
    '''
    print_log('INFO: generate_project_tcl()')
    # In the TopModule.hdlgen file, in the label <HDLGen> <ProjectManager> <settings> <environment>
    # You can get the location of the Package folder, and the mainPackage.hdlgen is under the Package folder
    # And under the mainPackage.hdlgen, in the label <HDLGen> <components>, you will see many <component> label
    # And each component label has a <dir> label, the <dir> label contains the path of hdl of each subconponents
    # Use TCL command `set_global_assignment -name VHDL_FILE path_of_the_hdl_file` to add those files into the Quartus project
    # Also add the MainPackage.vhd under the project folder into the Quartus project through the Tcl
    
    # HDL_n_Tcl.py is a python module which store the Tcl script
    # the structure of DE10_NANO_SoC_GHRD.tcl will be like:
    #   QUARTUS_PROJECT_TCL_PART_1 (a string variable in HDL_n_Tcl.py which store the Tcl template)
    #   the TCL command about adding VHD files into the quartus project
    #   QUARTUS_PROJECT_TCL_PART_2
    # then generate the DE10_NANO_SoC_GHRD.tcl

    # load hdlgen project xml
    project = minidom.parse(HDLGen_project_path)

    # Extract package folder location
    project_env = project.getElementsByTagName("environment")[0]
    mainPackage_hdlgen_path = project_env.firstChild.data + r'\Package\mainPackage.hdlgen'
    print_log(f'INFO: path of mainPackage.hdlgen: {mainPackage_hdlgen_path}')

    # Parse mainPackage.hdlgen for component paths
    main_package = minidom.parse(mainPackage_hdlgen_path)
    components = main_package.getElementsByTagName("component")

    vhdl_file_paths = list()
    tcl_commands = list()

    if components:
        for component in components:
            dir_tag = component.getElementsByTagName('dir')[0]
            vhdl_path = dir_tag.firstChild.data.replace('\\','/')
            vhdl_file_paths.append(vhdl_path)

        # Construct TCL commands to add VHDL files to Quartus project
        tcl_commands = [f'set_global_assignment -name VHDL_FILE {path}' for path in vhdl_file_paths]

    # And the top module itself to the commands
    project_name = project.getElementsByTagName("name")[0].firstChild.data
    top_module_vhdl_path = (project.getElementsByTagName('location')[0].firstChild.data + r'\VHDL\model' + f'\{project_name}.vhd').replace('\\','/')
    tcl_commands.append(f'set_global_assignment -name VHDL_FILE {top_module_vhdl_path}')

    # Add MainPackage.vhd to the commands
    main_package_vhd_path = (project_env.firstChild.data + r'\Package\MainPackage.vhd').replace('\\','/')
    tcl_commands.append(f'set_global_assignment -name VHDL_FILE {main_package_vhd_path}')

    # Combine with template parts from HDL_n_Tcl.py
    full_tcl_script = "\n".join([QUARTUS_PROJECT_TCL_PART_1] + tcl_commands + [QUARTUS_PROJECT_TCL_PART_2])

    # Save the TCL scripr
    with open(output_path + 'DE10_NANO_SoC_GHRD.tcl', 'w') as tcl_file:
        tcl_file.write(full_tcl_script)    





def generate_top_module(design_name, ports, pios, connections, output_path = ''):
    '''
    This function is to generate the top module of the entire soc system, which means connects user design to the Avalon MM bus
    '''
    wires_list = list()
    component_list = list()
    soc_system_list = list()
    for pio in pios:
        wires_list.append(f'wire [63:0] {pio.export_name};')
        soc_system_list.append(f'               .{pio.export_name}_export({pio.export_name}),')
    component_list.append(f'{design_name} my_{design_name} (')
    component_list.append('    .clk(fpga_clk_50),')
    for connection in connections:
        port_name = ports[connection[0]].name
        export_name = pios[connection[1]].export_name
        component_list.append(f'    .{port_name}({export_name}[{connection[2]}:{connection[3]}]),')
    component_list.append(r');')
    top_module = "\n".join([TOP_MODULE_HDL_PART_1] + wires_list + component_list + [TOP_MODULE_HDL_PART_2] + soc_system_list + [TOP_MODULE_HDL_PART_3])
    with open(output_path + 'DE10_NANO_SoC_GHRD.v', 'w') as verilog_file:
        verilog_file.write(top_module)    





def generate_qsys_tcl(pios, output_path = ''):
    print_log(f"INFO: generate_qsys_tcl()")
    # First, go through the list pios, add the instance according to the pio name in pios
    # Go through the list pios, generate the interface according to the export_name and pio_name.pio_mode in pios
    # Go through the list pios, generate the connection according to the address in pios
    set_instance_list = list()
    set_interface_list = list()
    set_connection_list = list()
    # add_interface clk clock sink
    # set_interface_property clk EXPORT_OF clk_0.clk_in
    set_interface_list.append(r'add_interface clk clock sink')
    set_interface_list.append(r'set_interface_property clk EXPORT_OF clk_0.clk_in')
    set_interface_list.append(r'add_interface hps_0_h2f_reset reset source')
    set_interface_list.append(r'set_interface_property hps_0_h2f_reset EXPORT_OF hps_0.h2f_reset')
    # connection
    set_connection_list.append(r'''add_connection clk_0.clk hps_0.h2f_axi_clock

add_connection clk_0.clk mm_bridge_0.clk''')
    for pio in pios:
         set_connection_list.append(f'add_connection clk_0.clk {pio.pio_name}.clock')

    set_connection_list.append(r'add_connection clk_0.clk_reset mm_bridge_0.reset')
    for pio in pios:
         set_connection_list.append(f'add_connection clk_0.clk_reset {pio.pio_name}.reset')

    set_connection_list.append(r'''
add_connection hps_0.h2f_axi_master mm_bridge_0.s0
set_connection_parameter_value hps_0.h2f_axi_master/mm_bridge_0.s0 arbitrationPriority {1}
set_connection_parameter_value hps_0.h2f_axi_master/mm_bridge_0.s0 baseAddress {0x0000}
set_connection_parameter_value hps_0.h2f_axi_master/mm_bridge_0.s0 defaultConnection {0}
                               ''')
    
    for pio in pios:
        # add_instance pio64_in_0 pio64_in 1.0
        set_instance_list.append(f'add_instance {pio.pio_name} pio64_{pio.mode} 1.0')
        # add_interface fifocontrolsignal conduit end
        # set_interface_property fifocontrolsignal EXPORT_OF pio64_out_1.pio64_out
        set_interface_list.append(f'add_interface {pio.export_name} conduit name')
        set_interface_list.append(f'set_interface_property {pio.export_name} EXPORT_OF {pio.pio_name}.pio64_{pio.mode}')
        # connection
        set_connection_list.append(f'add_connection mm_bridge_0.m0 {pio.pio_name}.s0')
        set_connection_list.append(f'set_connection_parameter_value mm_bridge_0.m0/{pio.pio_name}.s0 arbitrationPriority {1}')
        print_log(f'INFO: pio address: {pio.address}')
        hex_str = '{0x'+f"{pio.address:04x}"+'}'
        print_log(f'INFO: pio address hex: {hex_str}')
        set_connection_list.append(f'set_connection_parameter_value mm_bridge_0.m0/{pio.pio_name}.s0 baseAddress {hex_str}')
        set_connection_list.append(f'set_connection_parameter_value mm_bridge_0.m0/{pio.pio_name}.s0 defaultConnection {0}')
    # add_interface hps_0_h2f_reset reset source
    # set_interface_property hps_0_h2f_reset EXPORT_OF hps_0.h2f_reset
    # add_interface memory conduit end
    # set_interface_property memory EXPORT_OF hps_0.memory
    # add_interface reset reset sink
    # set_interface_property reset EXPORT_OF clk_0.clk_in_reset
    # set_interface_list.append(r'add_interface hps_0_h2f_reset reset source')
    # set_interface_list.append(r'set_interface_property hps_0_h2f_reset EXPORT_OF hps_0.h2f_reset')
    set_interface_list.append(r'add_interface memory conduit end')
    set_interface_list.append(r'set_interface_property memory EXPORT_OF hps_0.memory')
    set_interface_list.append(r'add_interface reset reset sink')
    set_interface_list.append(r'set_interface_property reset EXPORT_OF clk_0.clk_in_reset')

    qsys_tcl_end_1 = r'''set_interconnect_requirement {$system} {qsys_mm.clockCrossingAdapter} {HANDSHAKE}
set_interconnect_requirement {$system} {qsys_mm.maxAdditionalLatency} {1}
'''
    # qsys_tcl_end_2 = r'save_system {' + output_path + r'soc_system.qsys}'
    qsys_tcl_end_2 = r'save_system {soc_system.qsys}'

    full_qsys_tcl_script = "\n".join([QSYS_TCL_PART_1] + set_instance_list + set_interface_list + set_connection_list + [qsys_tcl_end_1, qsys_tcl_end_2])
    with open(output_path + 'soc_system.tcl', 'w') as tcl_file:
        tcl_file.write(full_qsys_tcl_script)    





def generate_xml_file(ports, pios, connections, testbench, output_path = ''):
    '''
    This function is to generate a xml file, this file will be transferred to DE10 Nano, then the python program in the DE10 Nano will interpret this xml file, and set up the map of connection.
    '''
    doc = minidom.Document()
    # create the root element: soc_system, which is the parent of design and testbench
    root_element = doc.createElement('soc_system')
    doc.appendChild(root_element)
    # create the element: design
    design_element = doc.createElement('design')
    root_element.appendChild(design_element)
    for connection in connections:
        port = ports[connection[0]]
        pio = pios[connection[1]]
        # create port node
        port_element = doc.createElement('port')
        design_element.appendChild(port_element)
        # create port name node, child of port
        port_name = doc.createElement('port_name')
        name_txt = doc.createTextNode(port.name)
        port_name.appendChild(name_txt) # add the text into the port name node
        port_element.appendChild(port_name) # add the node under its parent
        # create address node, child of port
        address = doc.createElement('address')
        address_txt = doc.createTextNode(f'{pio.address}')
        address.appendChild(address_txt)
        port_element.appendChild(address)
        # create start bit node, child of port
        start_bit = doc.createElement('start_bit')
        start_bit_txt = doc.createTextNode(f'{connection[2]}')
        start_bit.appendChild(start_bit_txt)
        port_element.appendChild(start_bit)
        # create end bit node, child of port
        end_bit = doc.createElement('end_bit')
        end_bit_txt = doc.createTextNode(f'{connection[3]}')
        end_bit.appendChild(end_bit_txt)
        port_element.appendChild(end_bit)
        # create mode node, child of port
        pio_mode = doc.createElement('pio_mode')
        pio_mode_txt = doc.createTextNode(pio.mode)
        pio_mode.appendChild(pio_mode_txt)
        port_element.appendChild(pio_mode)
    # create the element: test bench
    testbench_element = doc.createElement('testbench')
    testbench_txt = doc.createTextNode(testbench)
    testbench_element.appendChild(testbench_txt)
    root_element.appendChild(testbench_element)

    xml_str = doc.toprettyxml(indent="\t")

    with open(output_path + "soc_system.xml", "w") as f:
        f.write(xml_str)
        
        



def run_command(command, description):
    try:
        result = subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f'ERROR: Failed to execute command {description}, exit code {e.returncode}')
    else:
        print_log(f"INFO: Execute command {description} successfully")





def compile_programable_file(quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path, TopModuleName, path=''):
    '''
    This function aims to generate the project and compile the project.
    '''
    print_log(r'INFO: compile_programable_file()')
    # generate whole project
    command_generate_whole_project = f'{quartus_path} -t {path}\DE10_NANO_SoC_GHRD.tcl'
    run_command(command_generate_whole_project, 'to generate whole project')
    # generate platform designer project
    command_generate_platform_designer_project = f'{qsys_script_path} --script={path}\soc_system.tcl'
    run_command(command_generate_platform_designer_project, 'to generate platform designer system')
    # generate vhdl code
    command_generate_vhdl_code = f'{qsys_generate_path} --synthesis=VHDL {path}\soc_system.qsys'
    run_command(command_generate_vhdl_code, 'to generate vhdl code')
    # compile the project
    command_compile_project = f'{quartus_path} --flow compile {path}\DE10_NANO_SoC_GHRD.qpf'
    run_command(command_compile_project, 'to compile the project')
    # convert the programable file
    command_programable_file_convert = f'{quartus_cpf_path} -c {path}\output_files\DE10_NANO_SoC_GHRD.sof {TopModuleName}.rbf'
    run_command(command_programable_file_convert, 'to convert the programable file')



# this project_path end with \
def generate_bat_file(quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path, TopModuleName, project_path=''):


    bat_file_path = f'{project_path}generate_and_program.bat'

    with open(bat_file_path, 'w') as bat_file:
        bat_file.write(f'"{quartus_path}" -t DE10_NANO_SoC_GHRD.tcl\n')
        bat_file.write(f'"{qsys_script_path}" --script=soc_system.tcl\n')
        bat_file.write(f'"{qsys_generate_path}" --synthesis=VHDL soc_system.qsys\n')
        bat_file.write(f'"{quartus_path}" --flow compile "DE10_NANO_SoC_GHRD.qpf"\n')
        bat_file.write(f'"{quartus_cpf_path}" -c "output_files\\DE10_NANO_SoC_GHRD.sof" {TopModuleName}.rbf\n')
        bat_file.write(f'pause\n')

    print_log("INFO: Batch file 'generate_and_program.bat' has been successfully created.")





def de10nano_project_generator(HDLGen_project_path, path, quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path):
    print_log(f"INFO: de10nano_project_generator()")
    project = minidom.parse(HDLGen_project_path)
    design_name = project.getElementsByTagName('name')[0].firstChild.data
    connection_list = list()
    ports = list()
    pios = list()
    entity_ioports = project.getElementsByTagName("entityIOPorts")[0]
    for signal in entity_ioports.getElementsByTagName("signal"):
        # got signal information from project xml
        name = signal.getElementsByTagName("name")[0].firstChild.data
        if name == 'clk':
            print_log('INFO: clk detected')
            continue
        mode = signal.getElementsByTagName("mode")[0].firstChild.data
        type_str = signal.getElementsByTagName("type")[0].firstChild.data 
        description = signal.getElementsByTagName("description")[0].firstChild.data 
        # save the port infromation in the list
        port = Port(name, mode, type_str, description)
        print_log(f"INFO: signal name: {port.name}, signal mode: {port.mode}, signal type: {port.type_str}, signal width: {port.width}")

        ports.append(port)
        #   if:
        #       1, no pio exist yet
        #       2, pio don't have enough bit
        #       3, the existing pio direction is not suitable for this port
        #   need to create a new pio
        if len(pios) == 0 or pios[-1].mode != mode_convert(port.mode) or port.width > pios[-1].available_bit + 1:
            pio = Pio(f"pio_{mode_convert(port.mode)}_{len(pios)}", mode_convert(port.mode), int(8*len(pios)))
            pios.append(pio)
        start_bit = pio.available_bit
        pios[-1].connect(port.width)
        end_bit = pio.available_bit + 1
        connection_list.append((len(ports) - 1, len(pios) - 1, start_bit, end_bit))
        print_log(f"INFO: port index: {len(ports) - 1}, pio index: {len(pios) - 1}, start bit: {start_bit}, end bit: {end_bit}")
    
    # just check the connection information
    print_log(f'INFO: number of port: {len(ports)}')
    print_log(f'INFO: number of pio: {len(pios)}')
    for connection in connection_list:
        print_log(f'INFO: Connection Information: port index: {connection[0]}, pio index: {connection[1]}, start bit: {connection[2]}, end bit: {connection[3]}')
        print_log(f'INFO: Name of Port {connection[0]}: {ports[connection[0]].name}')
        print_log(f'INFO: Mode of Port {connection[0]}: {ports[connection[0]].mode}')
        print_log(f'INFO: Type_str of Port {connection[0]}: {ports[connection[0]].type_str}')
        print_log(f'INFO: Mode of Width {connection[0]}: {ports[connection[0]].width}')
        print_log(f'INFO: Name of PIO {connection[1]}: {pios[connection[1]].pio_name}')
        print_log(f'INFO: Name of Export {connection[1]}: {pios[connection[1]].export_name}')
        print_log(f'INFO: Mode of PIO {connection[1]}: {pios[connection[1]].mode}')
        print_log(f'INFO: Address of PIO {connection[1]}: {pios[connection[1]].address}')

    # I have already get the information of connection
    # According to the connection<List>, I can generate the soc_system.tcl! And the top module of HDL!
    
    # But first, I need to create the folder
    if not os.path.exists(path):
        os.makedirs(path)

    # Then prepare the necessery files in the folder
        
    # write the _hw.tcl file
    pio_in_tcl_file_name = 'pio64_in_hw.tcl'
    
    with open(path + pio_in_tcl_file_name, 'w') as file:
        file.write(PIO64_IN_HW_TCL)

    pio_out_tcl_file_name = 'pio64_out_hw.tcl'

    with open(path + pio_out_tcl_file_name, 'w') as file:
        file.write(PIO64_OUT_HW_TCL)

    # write the sv file
    ip_path = path + 'ip\pio64' # create the path first if not exist
    if not os.path.exists(ip_path):
        os.makedirs(ip_path)
    
    pio_in_hdl_sv_file_name = '\pio64_in.sv'

    with open(ip_path + pio_in_hdl_sv_file_name, 'w') as file:
        file.write(PIO64_IN_HDL_SV)

    pio_out_hdl_sv_file_name = '\pio64_out.sv'

    with open(ip_path + pio_out_hdl_sv_file_name, 'w') as file:
        file.write(PIO64_OUT_HDL_SV)
    

    # Then I can generate the project
        
    # Generate the Quartus project tcl
    generate_project_tcl(HDLGen_project_path, path)
        
    # Generate the Quartus top module
    generate_top_module(design_name, ports, pios, connection_list, path)
    
    # Generate the Qsys tcl
    generate_qsys_tcl(pios, path)

    # Generate the xml file
    testbench = project.getElementsByTagName('TBNote')[0].firstChild.data
    generate_xml_file(ports, pios, connection_list, testbench, path)

    # compile
    # compile_programable_file(quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path, design_name, path)

    # Generate the bat file
    generate_bat_file(quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path, design_name, path)
            




if __name__ == '__main__':
    quartus_path = r'C:\intelFPGA_lite\22.1std\quartus\bin64\quartus_sh.exe'
    qsys_script_path = r'C:\intelFPGA_lite\22.1std\quartus\sopc_builder\bin\qsys-script.exe'
    qsys_generate_path = r'C:\intelFPGA_lite\22.1std\quartus\sopc_builder\bin\qsys-generate.exe'
    quartus_cpf_path = r'C:\intelFPGA_lite\22.1std\quartus\bin64\quartus_cpf.exe'

    de10nano_project_generator(r'FIFO/FIFOTopModule/HDLGenPrj/FIFOTopModule.hdlgen', 'FIFO\\intelPrj\\', quartus_path, qsys_script_path, qsys_generate_path, quartus_cpf_path)
    #generate_project_tcl(r'FIFOTopModule/HDLGenPrj/FIFOTopModule.hdlgen')





