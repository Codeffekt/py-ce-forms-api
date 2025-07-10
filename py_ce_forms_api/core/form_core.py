from abc import ABC, abstractmethod

class FormCore(ABC):
    
    @abstractmethod
    def get_form(self) -> dict:
        pass