from pyaml.common.element import Element
from pyaml.common.holders.element_holder import ElementHolder


class DispatchElement(Element):
    def _fill_device(self, holder: ElementHolder) -> None:
        holder.filled_elements.append(self)


class DispatchHolder(ElementHolder):
    def __init__(self):
        super().__init__()
        self.filled_elements = []

    def create_magnet_strength_aggregator(self, magnets):
        return None

    def create_magnet_hardware_aggregator(self, magnets):
        return None

    def create_bpm_aggregators(self, bpms):
        return [None, None, None]

    def _fill_magnet(self, magnet) -> None:
        raise AssertionError("Unexpected magnet dispatch")

    def _fill_combined_function_magnet(self, magnet) -> None:
        raise AssertionError("Unexpected combined-function magnet dispatch")

    def _fill_serialized_magnets(self, magnets) -> None:
        raise AssertionError("Unexpected serialized magnet dispatch")

    def _fill_bpm(self, bpm) -> None:
        raise AssertionError("Unexpected BPM dispatch")

    def _fill_rf_plant(self, rf_plant) -> None:
        raise AssertionError("Unexpected RF plant dispatch")

    def _fill_betatron_tune_monitor(self, monitor) -> None:
        raise AssertionError("Unexpected betatron tune monitor dispatch")

    def _fill_tool(self, tool) -> None:
        raise AssertionError("Unexpected tool dispatch")

    def _fill_unbound_element(self, element) -> None:
        raise AssertionError("Unexpected unbound element dispatch")


def test_fill_device_delegates_to_elements():
    holder = DispatchHolder()
    elements = [DispatchElement("FIRST"), DispatchElement("SECOND")]

    holder.fill_device(elements)

    assert holder.filled_elements == elements
