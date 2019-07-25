import warnings

import numpy

from qcodes import ParameterWithSetpoints
from qcodes.instrument_drivers.Keysight.keysightb1500 import KeysightB1500, \
    MessageBuilder, constants
from qcodes.instrument_drivers.Keysight.keysightb1500.KeysightB1500_module \
    import parse_fmt_1_0_response, FMTResponse


class MeasurementNotTaken(Exception):
    pass


class SamplingMeasurement(ParameterWithSetpoints):
    """
    Performs sampling measurement using semiconductor
    parameter analyzer B1500A.
    """

    _timeout_response_factor = 10.00
    # This factor is a bit higher than the ratio between
    # the measured measurement-time and the calculated measurement
    # (from the user input). Check :get_raw: method to find its usage.

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.data = FMTResponse

    def _set_up(self):
        self.root_instrument.write(MessageBuilder().fmt(1, 0).message)

    def get_raw(self):
        """
        Sets up the measurement by calling :_set_up:

        Automatically sets up the visa time out.

        The visa time-out should be longer than the time it takes to finish
        the sampling measurement. The reason is that while measurement is
        running the data keeps on appending in the buffer of SPA. Only when
        the measurement is finished the data is returned to the VISA handle.
        Hence during this time the VISA is idle and waiting for the response.
        If the timeout is lower than the total run time of the measurement,
        VISA will give error.

        We set the Visa timeout to be the measurement_time times the
        `_timeout_response_factor`. Strictly speaking the timeout should be
        just higher the measurement time.

        Return:
            numpy array with sampling measurement
        """
        try:
            measurement_time = self.instrument._total_measurement_time()
            # set time out to this value
            time_out = measurement_time * self._timeout_response_factor

            # default timeout
            default_timeout = self.root_instrument.timeout()

            # if time out to be set is lower than the default value
            # then keep default
            if time_out < default_timeout:
                time_out = default_timeout

            with self.root_instrument.timeout.set_to(time_out):
                self._set_up()
                raw_data = self.root_instrument.ask(
                    MessageBuilder().xe().message)
                self.data = parse_fmt_1_0_response(raw_data)
            return numpy.array(self.data.value)
        except TypeError:
            raise Exception('set timing parameters first')

    def compliance(self):
        """
        check for the status other than "N" (normal) and output the
        number of data values which were not measured under "N" (normal)
        status.

        For the list of all the status values and their meaning refer to
        :class:`constants.ComplianceStatus`.

        """

        if isinstance(self.data.status, list):
            data = self.data
            total_count = len(data.status)
            normal_count = data.status.count('N')
            exception_count = total_count - normal_count
            if total_count == normal_count:
                print('All measurements are normal')
            else:
                indices = [i for i, x in enumerate(data.status)
                           if x == "C" or x == "T"]
                warnings.warn(f'{str(exception_count)} measurements were '
                              f'out of compliance at {str(indices)}')

            compliance_error_list = constants.ComplianceErrorList
            compliance_list = [compliance_error_list[key].value
                               for key in data.status]
            return compliance_list
        else:
            raise MeasurementNotTaken('First run sampling_measurement'
                                      ' method to generate the data')
