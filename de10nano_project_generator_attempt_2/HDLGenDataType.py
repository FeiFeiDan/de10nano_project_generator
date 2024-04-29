from dataclasses import dataclass
from typing import List, Tuple
import re

@dataclass
class Port:
    _name: str
    _direction: str
    _type: str
    _width: int = -1

    def __post_init__(self):
        self.name = self._name
        self.direction = self._direction
        self.type = self._type

    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Name must be a string. {value} is a {type(value)}")
        self._name = value

    @property
    def direction(self) -> str:
        return self._direction
    
    @direction.setter
    def direction(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f"Direction(Mode) must be a string. {value} is a {type(value)}")
        if value not in {'in', 'out'}:
            raise ValueError(f'Type {value} not supported yet.')
        self._direction = value

    @property
    def type(self) -> str:
        return self._type
    
    @type.setter
    def type(self, value) -> None:
        if not isinstance(value, str):
            raise ValueError(f'Type must be a string. {value} is a {type(value)}')
        if not self.__type_parser(value):
            raise ValueError(f'{value} is not a supported type (single bit or bus)')
        self._type = value
        
    def __type_parser(self, value: str) -> bool:
        match = re.match(r'(?:single bit|bus\(\s*(\d+)\s*downto\s*(\d+)\s*\))', value)
        if match:
            if match.group(0) == 'single bit':
                self._width = 1
                return True
            else:
                msb, lsb = map(int, match.groups())
                width = msb - lsb + 1
                if not (1 <= width <= 64):
                    raise ValueError(f'The width of {type} {width} is not in [1, 64]')
                self._width = width
                return True
        return False

    @property
    def width(self) -> int:
        return self._width
       

@dataclass
class PIO:
    _pio_name: str
    _direction: str
    _address: int
    _available_bit: int = 63

    def __post_init__(self):
        self.pio_name = self._pio_name
        self.direction = self._direction
        self.address = self._address

    @property
    def pio_name(self) -> str:
        return self.pio_name
    
    @pio_name.setter
    def pio_name(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f'PIO name must be a string, {value} is a {type(value)}')
        self._pio_name = value

    @property
    def direction(self) -> str:
        return self._direction
    
    @direction.setter
    def direction(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError(f'Direction must be a string, {value} is a {type(value)}')
        if not (value == 'in' or value == 'out'):
            raise ValueError(f'{value} was recevied but only IN and OUT is supported.')
        self._direction = value

    @property
    def address(self) -> int:
        return self._address
    
    @address.setter
    def address(self, value: int) -> None:
        if not isinstance(value, int):
            raise ValueError(f'address must be a int, {value} is a {type(value)}')
        self._address = value

    @property
    def available_bit(self) -> int:
        return self._available_bit
    
    def connect_port(self, port: Port) -> int:
        return self._connect_to_available_bits(port)
        
    def has_spare_space_for(self, port_width: int) -> bool:
        return self.available_bit + 1 > port_width

    def _connect_to_available_bits(self, port: Port) -> int:
        start_bit = self._available_bit
        self._available_bit -= port.width
        return start_bit



@dataclass
class PortPIOAdapter:
    _pios: List[PIO] = []

    def _direction_convert(mode: str) -> str:
        return 'in' if mode == 'out' else 'out'

    def connect_port(self, port: Port) -> Tuple[PIO, int]:
        pio = self._find_or_create_pio_for_port(port)
        start_bit = pio.connect_port(port)
        return pio, start_bit

    def _find_or_create_pio_for_port(self, port: Port) -> PIO:
        for pio in self._pios[::-1]:
            if pio.direction == self._direction_convert(port.direction):
                if pio.has_spare_space_for(port.width):
                    return pio
            
        pio_name = f'pio_{len(self._pios)}'
        pio_direction = self._direction_convert(port.direction)
        pio_address = 8 * len(self._pios)
        pio = PIO(pio_name, pio_direction, pio_address)
        self._pios.append(pio)
        return pio
    

