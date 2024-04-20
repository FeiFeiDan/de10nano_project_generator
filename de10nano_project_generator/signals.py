import re

class PIO:
    def __init__(self, name: str, mode: int, address: int):
        """
        Initialize a PIO object, setting its name, mode, address, and available bit information.
        
        Parameters:
        - name (str): The name of the PIO.
        - mode (int): The operating mode of the PIO.
        - address (int): The hardware address of the PIO.
        
        Variables:
        - self.mode: The current operating mode of the PIO.
        - self.available_bit: The current number of available bits, initialized as 63 indicating the highest available bit;
          it should be set to -1 when all PIO resources are exhausted.
        - self.pio_name: The name of the PIO.
        - self.export_name: The exported name for the PIO, derived from the PIO's name.
        - self.address: The hardware address of the PIO.

        """
        self.mode = mode
        self.available_bit = 63  # Indicates the highest available bit; should be -1 when the PIO is fully occupied
        self.pio_name = name
        self.export_name = f"{name}_export"
        self.address = address

    def connect(self, width: int) -> None:
        """
        Connects a resource with a width of `width` to the PIO.

        Raises an AssertionError if there are not enough available bits to fulfill the required width.

        Parameters:
        - width (int): The width of the resource to allocate to the PIO.

        Raises:
        - AssertionError: If there are insufficient available bits to meet the requested width.
        """
        assert self.available_bit + 1 >= width, "ERROR: Not enough available bits for the required resource width."
        self.available_bit -= width

class Port:
    def __init__(    self,
                    name: str,
                    mode: str,
                    type_str: str,
                    description: str,
                ):
        """
        Initialize a Port object, setting its name, mode, type string, description, and width.

        Parameters:
        - name (str): The name of the port.
        - mode (str): The operating mode of the port.
        - type_str (str): A string that describes the type and size of the port.
        - description (str): A description of the port's functionality.

        Variables:
        - self.name: The name of the port.
        - self.mode: The current operating mode of the port.
        - self.type_str: The type string describing the port.
        - self.description: The description of the port.
        - self.width: The width of the port, calculated based on the provided type string.

        """
        self.name = name
        self.mode = mode
        self.type_str = type_str
        self.description = description
        self.width = self.calculate_port_width(type_str)

    def calculate_port_width(self, type_str: str) -> int:
        """
        Determine the width of the port based on the provided type string.

        If the type string represents a single bit or a bus range (e.g., "bus(5 downto 0)"),
        the method calculates the width accordingly. Otherwise, it raises an error.

        Parameters:
        - type_str (str): The type string to parse.

        Returns:
        - int: The width of the port.

        Raises:
        - ValueError: If the higher bit index is smaller than the lower bit index in a bus range.
        - AssertionError: If the signal type is not currently supported.
        """
        match = re.match(r'(?:single bit|bus\(\s*(\d+)\s*downto\s*(\d+)\s*\))', type_str)
        if match:
            if match.group(0) == 'single bit':
                return 1
            else:
                start, end = map(int, match.groups())
                if start > end:
                    return start - end + 1
                else:
                    raise ValueError(f"ERROR: Higher bit index ({start}) is smaller than lower bit index ({end}).")
        else:
            assert False, f"ERROR: Signal type '{type_str}' is not supported yet."