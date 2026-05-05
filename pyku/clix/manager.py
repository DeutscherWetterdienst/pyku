#!/usr/bin/env python3
"""
Manager interface for climate-indicator tool.
Handles classes and functions used in the core program
"""

import glob
import importlib
import inspect
import re
from dataclasses import dataclass
from typing import Optional

import xarray as xr
import xclim
from xclim.core.units import check_units

from pyku import logger
from pyku.clix import indicator_data


@dataclass
class Threshold:
    threshold_name: str
    standard_name: str
    input_data: str
    value: float
    units: str
    units_metadata: Optional[str] = None
    condition: str = "unknown"

    def __post_init__(self):

        if self.units_metadata is None:
            # Check for temperature units
            try:
                if check_units(val=self.units_metadata, dim="[temperature]"):
                    # always on scale for thresholds
                    self.units_metadata = "temperature: on scale"
            except (ValueError, TypeError):
                pass

    def to_dict(self):
        data = {
              "threshold_name": self.threshold_name,
              "standard_name": self.standard_name,
              "input": self.input_data,
              "value": self.value,
              "units": self.units,
              }
        if self.units_metadata is not None:
            data["units_metadata"] = self.units_metadata

        # cosmetics just to keep "units" and "units_metadata" together
        data["condition"] = self.condition

        return data

    def to_xarray(self) -> xr.DataArray:
        """
        Converts the object's data into an xarray DataArray.

        The DataArray's name will be `threshold_name`.
        The DataArray's data will be `value`.
        All other dictionary keys (standard_name, input, units, condition,
        units_metadata) will be added as attributes (attrs) to the DataArray.

        Returns:
            xr.DataArray: An xarray DataArray representing the processed data.
        """
        thres_dict = self.to_dict()

        # Extract the core components for the DataArray
        da_name = thres_dict.pop("threshold_name")  # Remove from dict
        da_value = thres_dict["value"]

        # The remaining items in thres_dict will become attributes
        # for easier readability with ncdump, the value becomes an attribute
        thres_dict["value"] = str(thres_dict["value"])
        da_attrs = thres_dict

        # Since value is always a scalar, we don't need to pass coords or dims
        # xarray will automatically create a scalar DataArray.
        data_array = xr.DataArray(
            data=da_value,
            name=da_name,
            attrs=da_attrs
        )

        return data_array


@dataclass
class Duration:
    duration_name: str
    value: float
    unit: str
    condition: str

    def to_dict(self):
        return {
            "duration_name": self.duration_name,
            "value": self.value,
            "unit": self.unit,
            "condition": self.condition
        }

    def to_xarray(self) -> xr.DataArray:
        """
        Converts the object's data into an xarray DataArray.

        The DataArray's name will be `duration_name`.
        The DataArray's data will be `value`.
        All other dictionary keys (unit, condition)
        will be added as attributes (attrs) to the DataArray.

        Returns:
            xr.DataArray: An xarray DataArray representing the processed data.
        """
        thres_dict = self.to_dict()

        # Extract the core components for the DataArray
        da_name = thres_dict.pop("duration_name")  # Remove from dict
        da_value = thres_dict["value"]  # use as data

        # The remaining items in thres_dict will become attributes
        # for easier readability, the value remains as an attribute
        thres_dict["value"] = str(thres_dict["value"])
        da_attrs = thres_dict

        # Since value is always a scalar, we don't need to pass coords or dims
        # xarray will automatically create a scalar DataArray.
        data_array = xr.DataArray(
            data=da_value,
            name=da_name,
            attrs=da_attrs
        )

        return data_array


class ClimateIndicator:
    def __init__(self, name, frequency, params={}):
        self.name = name
        self.long_name = indicator_data[name].get('long_name')
        self.standard_name = indicator_data[name].get('standard_name')
        self.func_name = indicator_data[name]['function']
        xclim.set_options(check_missing="any")  # check_missing="wmo")
        self.func = load_function(self.func_name)
        self.xclim_indicator_info = get_xclim_indicator_info(name)

        self.default_params = indicator_data[name].get(
            'default_parameters', {})

        self.signature = inspect.signature(self.func)
        self.required_args = {
            k: v.annotation for k, v in self.signature.parameters.items()
            if v.default is inspect.Parameter.empty
            if v.annotation is not inspect.Parameter.empty
        }

        if params:
            self.optional_args = {**params}
        else:
            self.optional_args = {**self.default_params}

        # Set required frequency as optional argument
        self.optional_args['freq'] = frequency

        # Reduce required args
        self.required_args = {k: v for k, v in self.required_args.items()
                              if k not in self.optional_args}

        # The input variables for the functions used in xclim are
        # determined using the "DataArray" string in the inspected
        # arguments of the xclim functions
        self.input_vars = {k: v for k, v in self.required_args.items()
                           if "DataArray" in v}

        if indicator_data[name].get('input_vars', None):
            self.input_vars = {k: "DataArray"
                               for k in indicator_data[name].get('input_vars')}
            for key, ivar in zip(self.required_args.keys(),
                                 self.input_vars.keys()):
                # Reinitialize required args with provided input keys
                self.required_args[key] = ivar
        else:
            self.required_args = {k: k for k in self.required_args.keys()}

        self.thresholds = self.get_thresholds()
        self.operators = self.get_operators()

        # Check if climate indicator is percentile based
        self.is_perc_indicator = any('per' in key for key in self.input_vars)

    def xclim_indicator_info(self):
        '''
        Get metadata information from xclims "indicator" files
        Information available for specific xclim indicators,
        but not for generic functions
        '''

        # try to get metadata from xclim - indicators
        xclim_ind_name = \
            indicator_data[self.name]['function'].split('.')[-1]
        indicator_obj = \
            xclim.core.indicator.registry.get(xclim_ind_name.upper())

        if indicator_obj is not None:
            indicator_attrs = indicator_obj.get_instance()
        else:
            indicator_attrs = None

        return xclim_ind_name, indicator_attrs

    def get_thresholds(self):
        """Function to return thresholds"""

        thres = {k: v for k, v in self.optional_args.items()
                 if "thres" in k}
        return thres

    def get_operators(self):
        """Function to return operators"""

        op_list = [">", "gt", "<", "lt", ">=",
                   "ge", "<=", "le", "=", "eq"]
        operators = {k: v for k, v in self.optional_args.items()
                     if "op" in k and v in op_list}
        return operators

    def get_duration(self):
        """Function to return operators"""

        duration = {k: v for k, v in self.optional_args.items()
                    if "window" in k}
        return duration

    def __call__(self):
        """Call the function with validated arguments."""
        kwargs = {**self.required_args, **self.optional_args}
        return self.func(**kwargs)


def get_xclim_indicator_info(indicator):

    '''
    Get metadata information from xclims "indicator" module using the
    function names
    Information available for specific xclim indicators, but not for
    generic functions
    '''

    from xclim.core.indicator import registry

    # Read xclim function name from yaml-configuration
    func_name = indicator_data[indicator]['function']

    # Try to get metadata from xclim.core.indicators
    ind_name = func_name.split('.')[-1]

    # Exception...idk...do we have to take exceptions into account?
    # Are there many of this kind...???
    # Automate the looking up of correct indicator using registry.values
    # somehow!
    if ind_name == 'precip_accumulation':
        ind_name = 'prcptot'
    elif ind_name == 'max_1day_precipitation_amount':
        ind_name = 'rx1day'

    indicator_obj = registry.get(ind_name.upper())

    if indicator_obj is not None:
        indicator_attrs = indicator_obj.get_instance()
    else:
        indicator_attrs = None

    return indicator_attrs


def get_indicator_description(indicator):

    '''
    Trying to get indicator_description from xclim indicator
    attributes.
    Fallback option is to use the description from the
    yaml-configuration file.
    '''

    indicator_attrs = get_xclim_indicator_info(indicator)

    if indicator_attrs is not None:
        cf_attrs = getattr(indicator_attrs, 'cf_attrs')[0]
        indicator_descr = cf_attrs['long_name']
    else:
        try:
            indicator_descr = indicator_data[indicator]['description']
        except KeyError:
            logger.error(f'''
            No indicator description found for {indicator} in
            xclim indicator module and no description given in yaml
            configuration file!''')
            exit()

    return indicator_descr


def replace_description_with_values(parser, indicator_descr):
    """
    Replace placeholders in a description string with default values from a
    parser's arguments.

    For each action in the parser, this function looks for placeholders in the
    form `{arg_name}` inside the `indicator_descr` string and replaces them
    with the corresponding default values  defined in the parser. If a
    placeholder does not match any argument name, it is left unchanged.

    Args:
        parser: An `ArgumentParser` instance (e.g., from `jsonargparse`).
        indicator_descr (str): A template string with placeholders like
        `{thres}`, `{op}`, etc.

    Returns:
        str: The description string with placeholders replaced by argument
        defaults.
    """

    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    # Build a dictionary of all defaults from parser actions
    defaults = {
        action.dest: str(action.default)
        for action in parser._actions
        if getattr(action, 'dest', None) and action.default is not None
    }

    return indicator_descr.format_map(SafeDict(defaults))


def parse_thres(thres):
    """
    Parse a threshold value that may be a Pint Quantity or a string like "20
    degC".

    Args:
        thres (str or Quantity): Threshold to parse

    Returns:
        tuple:
            float: numeric value of the threshold
            str: unit of the threshold
    """
    # Handle Pint Quantity objects
    try:
        value = thres.magnitude
        unit = str(thres.units)
        return value, unit
    except AttributeError:
        pass  # Not a Quantity, proceed to string parsing

    # Handle string inputs
    if isinstance(thres, str):
        thres = thres.strip()
        match = re.match(
            r'^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)[\s]*([^\d\s].*)$',
            thres
        )
        if match:
            value = float(match.group(1))
            unit = match.group(2).strip()
            return value, unit
        else:
            raise ValueError(f"Invalid threshold format: '{thres}'")
    # maybe do not raise error, but give a logger warning and return None?
    raise TypeError(f"Unsupported type for threshold: {type(thres)}")


def threshold_names(thresholds, varnames, ds_list):
    """Generate renamed thresholds, associated input data, and standard names.

    Args:
        thresholds (dict): Original threshold dict.
        varnames (list): List of variable names (str) expected in each ds.
        ds_list (list): List of xarray.Dataset objects.

    Returns:
        tuple of (dict, dict, dict): new_thresholds, input_data, standard_names
    """

    new_thresholds = {}
    thres_input_data = {}
    standard_names = {}

    for i, key in enumerate(thresholds):
        # Match threshold key with a variable name
        matching_index = next((vidx for vidx, v in enumerate(varnames)
                               if v in key), None)
        var_ind = matching_index if matching_index is not None else i

        try:
            varname = varnames[var_ind]
        except IndexError:
            varname = None

        # Determine new threshold name
        if len(thresholds) == 1:
            thres_name = "threshold"
        elif varname:
            if key == 'threshold1' or key == 'threshold2' or \
               'threshold_var' in key:
                thres_name = f"threshold_{varname}"
            else:
                thres_name = key
        else:
            thres_name = key
            logger.info(
                f"""
                Could not assign a variable-based threshold name for
                '{key}'.
                Using original threshold key."""
            )

        # Store threshold value under new name
        new_thresholds[thres_name] = thresholds[key]

        # Input data string
        thres_input_data[thres_name] = f"data: {varname}" \
            if varname else "unknown"

        # Standard name extraction
        std_name = 'unknown'
        try:
            std_name = ds_list[var_ind][varname].attrs.get('standard_name',
                                                           std_name)
            if std_name == 'precipitation_flux' or \
               std_name == 'precipitation_rate':
                std_name = 'lwe_precipitation_rate'
        except (IndexError, KeyError, AttributeError, TypeError):
            logger.info(f"""
            Could not retrieve standard_name for threshold: {thres_name}""")

        standard_names[thres_name] = std_name
    return new_thresholds, thres_input_data, standard_names


def threshold_dataclasses(
        thresholds, operators, ds_vars, ds_vals, xclim_ind_name):
    """
    Create a list of Threshold dataclass instances from threshold definitions.

    This function combines threshold values, associated metadata, and logical
    conditions (operators) to generate structured Threshold objects.

    Parameters:
        thresholds (dict): Mapping of threshold keys to values
        operators (dict): Mapping of threshold keys to comparison operators
        ds_vars (iterable): List of variable names corresponding to threshold
        inputs.
        ds_vals (iterable): List of xarray Dataset objects containing metadata.
        xclim_ind_name (str): Name of the xclim indicator,

    Returns:
        List[Threshold]: A list of Threshold dataclass instances.
    """
    # strictly, we'd need to check each function and possibly include
    # exceptions; A possible case where there are e.g. 3 thresholds but 2
    # operators in the yaml is not covered. Did not see such a thing in the
    # xclim doc.

    fixed_conditions = {'dry': '<',
                        'wet': '>=',
                        'cooling_degree': '>',
                        'heating_degree': '<'}
    thresholds, thres_input_data, thres_standard_name = threshold_names(
                thresholds, list(ds_vars), list(ds_vals),
                )

    threshold_dataclasses = []
    operator_list = list(operators.values())

    for i, thres_key in enumerate(thresholds):
        value, unit = parse_thres(thresholds[thres_key])

        if len(operators) == 1:
            condition = next(iter(operators.values()), None)
        else:
            # Check if any key is a substring of the variable name
            matching_key = next(
                    (key for key in fixed_conditions
                     if xclim_ind_name and thres_key in xclim_ind_name), None
                    )
            if matching_key:
                condition = fixed_conditions[matching_key]  # here, the operator needs to be!  # noqa
            else:
                try:
                    condition = operator_list[i]
                except Exception:
                    condition = 'look up in function'

        t = Threshold(
                threshold_name=thres_key,
                standard_name=thres_standard_name[thres_key],
                input_data=thres_input_data[thres_key],
                value=value,
                units=unit,
                condition=condition
                )

        threshold_dataclasses.append(t)

    return threshold_dataclasses


def duration_dataclasses(duration):
    duration_dataclasses = []
    for key, value in duration.items():
        if len(duration) == 1:
            dur_name = "duration"
            dur_condition = ">="
        else:
            # some indices have a "start" and "stop" window
            dur_name = key
            dur_condition = "="

        d = Duration(
            duration_name=dur_name,
            value=value,
            unit='days',
            condition=dur_condition
        )
        duration_dataclasses.append(d)

    return duration_dataclasses


# To Add for both get_attrs functions: What happens if indicator is not defined in yaml?  # noqa
def get_global_attrs(indicator, varnames, xclim_attrs):
    """
    Generate global metadata attributes for a climate indicator.

    This function combines attributes from three sources:
    1. Predefined metadata from the loaded YAML file (`indicator_data`).
    2. Metadata from the corresponding xclim indicator object (`xclim_attrs`).
    3. Automatically generated input descriptions based on input variable names
    (`varnames`).

    If an attribute is already defined in the YAML file, it is not overwritten.
    A descriptive "input" field is constructed based on the number and type of
    input variables.

    Parameters:
        indicator (str): Name or key of the climate indicator.
        varnames (list of str): List of variable names used as inputs to the
        indicator.
        xclim_attrs (object): xclim indicator object, typically used for
        accessing attributes like title, abstract, and description.

    Returns:
        dict: Combined dictionary of global attributes for the indicator, ready
        to be assigned to netCDF metadata or documentation.
    """

    varnames = list(varnames)

    # Step 1: YAML-defined attributes
    global_attrs = indicator_data.get(indicator,
                                      {}).get('global_attrs', {}).copy()

    # A0.2: look for global attrs in xclim
    # fields = ["title", "abstract", "description"]
    # ToDo
    # - anomaly = "Anomaly respective to the reference period 1971 - 2000"?
    # - history = "Processing at Deutscher Wetterdienst"?
    # - value_type = "anomaly" ?

    # Step 2: Pull selected xclim attributes if not already in YAML
    fallback_fields = ["title", "abstract", "description"]
    for field in fallback_fields:
        if field not in global_attrs and hasattr(xclim_attrs, field):
            value = getattr(xclim_attrs, field)
            if value is not None:
                global_attrs[field] = value
            # maybe move this to the very end (and loop througth
            # global_attrs.items())
            # when thres is defined?
    # Step 3: Compose input description if missing
    if "input" not in global_attrs:
        if len(varnames) == 1:
            # ds_varmapping
            input_string = f"data: {varnames[0]}"
        elif any('per' in v for v in varnames):
            # found percentile input
            filtered_vars = [var for var in varnames
                             if 'per' not in var]
            if len(filtered_vars) == 1:
                input_string = f"data: {filtered_vars[0]}"
            elif len(filtered_vars) == 2:
                input_string = f"""
                data1: {filtered_vars[0]},
                data2: {filtered_vars[1]}"""
        elif len(varnames) == 2:
            # check for temperature data
            role_map = {
             "high_data": next((v for v in varnames if "max" in v), None),
             "low_data": next((v for v in varnames if "min" in v), None)
            }

            # desired string
            if "high_data" in role_map and "low_data" in role_map:
                input_string = ", ".join(f"{k}: {v}"
                                         for k, v in role_map.items())
            else:
                input_string = f"""
                data1: {varnames[0]},
                data2: {varnames[1]}"""
        else:
            input_string = ", ".join(f"data{i+1}: {v}"
                                     for i, v in enumerate(varnames))
        global_attrs['input'] = input_string

    return global_attrs


# def is_temperature_unit(unit_str):
#    try:
#        unit = units(unit_str)
#        return unit.dimensionality == units.degC.dimensionality
#    except Exception:
#        return False


def get_variable_attrs(indicator, xclim_attrs):
    """
    Retrieve variable attributes for a given indicator from multiple sources.

    This function aggregates variable metadata from:
    1. A YAML-like dictionary (`indicator_data`), which stores predefined
    attributes.
    2. The xclim indicator function attributes (`xclim_attrs`), providing
    defaults if not present in YAML.

    It selectively includes only certain standard fields and conditionally adds
    a `units_metadata` key if the units represent temperature.

    Parameters:
        indicator (str): The key/name of the climate indicator.
        xclim_attrs (object): The xclim indicator attributes object (typically
        a function or class instance).

    Returns:
        dict: A dictionary containing merged variable attributes with keys such
        as 'standard_name', 'long_name', 'units', 'cell_methods', and
        optionally 'units_metadata' if units are temperature-related.
    """

    fields = ["standard_name", "long_name", "units", "cell_methods"]
    # ToDo: for time variable: "climatology_bounds" instead of "time_bounds"
    # (not here)
    variable_attrs = {}

    indicator_entry = indicator_data.get(indicator, {})
    # extract from YAML file
    variable_attrs.update({
        key: indicator_entry[key]
        for key in fields
        if key in indicator_entry and indicator_entry[key] is not None
    })
    # fill missing fields from xclim_attrs
    for field in fields:
        if hasattr(xclim_attrs, field) and field not in variable_attrs:
            val = getattr(xclim_attrs, field)
            if val is not None:
                variable_attrs[field] = val

    # add units_metdata for temperature data
    units = variable_attrs.get("units")

    try:
        if check_units(val=units, dim="[temperature]"):
            # needs to be changed if anomaly == true
            # or use convert_units_to(xr.DataArray([2], attrs={"units":
            # "delta_degC"}), "K"))
            variable_attrs["units_metadata"] = "temperature: on_scale"
    except (ValueError, TypeError):
        pass

    return variable_attrs


def get_parameter_attr(
        optional_args,
        hasThreshold=False,
        isSpelllength=False,
        long_name=None):
    """
    Returns a comma-separated string of parameter attributes, if they apply.

    Parameters:
        hasThreshold (bool): Include "threshold, condition" if True
        isSpelllength (bool): Include "duration" if True
        long_name (str or None): Long Name from variable attributes

    Returns:
        str or None: Combined description of parameter attributes
    """
    parameter_string = []
    statistic_string = ['max', 'min', 'mean', 'sum', 'count',
                        'standard_deviation', 'percentile']
    if hasThreshold:
        parameter_string.append("threshold, condition")
    if isSpelllength:
        parameter_string.append("duration")

    value_list = ["mean", "sum", "max", "min", "std", "count"]

    # in some generic xclim functions, "op" is a statistic applied to the data
    # array
    stat = {k: v for k, v in optional_args.items()
            if "op" in k and v in value_list}

    # in sume xclim-functions, theres a spell_reducer
    spell_reduc = {k: v for k, v in optional_args.items()
                   if "spell_reducer" in k and v in value_list}
    if len(stat) == 1:
        parameter_string.append(f"statistic: {next(iter(stat.values()))}")
    if len(stat) > 1:
        logger.warning(f"""
        Expected only one statistical operator, but found multiple: {stat}""")

    if len(spell_reduc) == 1:
        parameter_string.append(f"""
        statistic: {next(iter(spell_reduc.values()))}""")
    elif len(spell_reduc) > 1:
        logger.warning(f"""
        Expected only one spell reducer, but found multiple: {stat}""")
    elif long_name is not None:
        for stat in statistic_string:
            if stat in long_name.lower():
                parameter_string.append(f"statistic: {stat}")
    if not parameter_string:
        return None

    parameter_string = ", ".join(parameter_string)

    return parameter_string


def load_function(func_path):
    """Dynamically import and retrieve function object."""
    *module_parts, func_name = func_path.rsplit('.')
    module = importlib.import_module(".".join(module_parts))

    if not hasattr(module, func_name):
        raise ValueError(f"The function {func_name} does not exist in the {module} library!")  # noqa

    return getattr(module, func_name)


def update_default_args(parser, default_params):
    """
    Update default function arguments with parameter provided by dict
    """

    for action in parser._actions:
        if action.dest in default_params.keys():
            action.default = default_params[action.dest]

    return


def validate_and_get_files_from_yaml_content(config_yaml):

    """
    Validates the given yaml configuration to find files by facets

    Return:
        List: (Nested) list of input files
    """

    import yaml
    from pyku.drs import list_drs_standards
    from pyku.find import get_files_by_drs
    from pyku.find import get_file_dataframe

    with open(config_yaml) as f:
        cfg = yaml.safe_load(f)

    if 'standard' not in cfg.keys():
        raise ValueError('You must provide a DRS standard (like standard: cordex).')  # noqa
    else:
        standard = cfg['standard']

    if standard not in list_drs_standards():
        raise ValueError(f"""Invalid DRS standard: {standard}. Must be one of
        pyku implemented standard: {' '.join(list(list_drs_standards()))} """)

    if 'root_dir' not in cfg.keys():
        raise ValueError(""" You must provide a root_dir (e.g.
        root_dir: /rootPath/to/DRS/structure/).""")
    else:
        root_dir = cfg['root_dir']

    if 'facets' not in cfg.keys():
        raise ValueError("""
        All facets must be listed under the "facets" keyword.""")
    else:
        facets = cfg['facets']

    # Get files using DRS facet search
    files = get_files_by_drs(standard=standard,
                             parent_dir=root_dir,
                             **facets)

    # Create dataframe containing cordex facets
    df = get_file_dataframe(files, standard=standard)

    # Find the column name containing "var"
    var_column = [c for c in df.columns if "var" in c][0]

    # Access the column
    variables = df[var_column].unique()

    ifiles = []
    for var in variables:
        df_filtered = df[df[var_column].isin([var])]
        ifiles.append(df_filtered['file'].tolist())

    return ifiles


def _has_wildcards(path_str: str) -> bool:
    return glob.has_magic(path_str)


def _has_braces(path_str: str) -> bool:
    return bool(re.search(r"\{.*\}", path_str))


def get_files(files):

    """
    Function to check given input file or input directories

    Parameters:
        files (str, list): Path(s) of file(s) or a directory/directories, where
        input files are located.

    Return: (Nested) List of files
    """

    from pathlib import Path
    from braceexpand import braceexpand

    if isinstance(files, str):
        files = [files]

    ifiles = []
    for ifile in files:
        ifile_path = Path(ifile)
        if ifile_path.is_file() and ifile_path.suffix == '.nc':
            ifiles.append([ifile])
        elif ifile_path.is_dir():
            files = list(ifile_path.glob('*.nc'))
            ifiles.append(files)
        elif _has_wildcards(ifile) or _has_braces(ifile):
            expanded = list(braceexpand(ifile))
            pat_files = []
            for pat in expanded:
                if glob.glob(pat):
                    pat_files.extend(glob.glob(pat))
            ifiles.append(pat_files)
        else:
            raise TypeError("Expected either a path to a netCDF file or a directory including nc-files.")  # noqa

    return ifiles


def sort_files_by_xclim_order(ifiles, input_vars, varnames):

    """
    Sorting files to correct order for indicator function call
    """

    from pyku.meta import get_geodata_varnames

    # Sort files in order for xclim call
    sorted_files = []

    if len(ifiles) == 1:
        return ifiles

    for iv in input_vars:
        for i, ifile in enumerate(ifiles):
            ds_varname = get_geodata_varnames(xr.open_dataset(ifile[0]))[0]
            if iv in ds_varname or iv in varnames:
                sorted_files.append(ifile)
                del ifiles[i]  # More efficient and avoids .remove() overhead
                break

    return sorted_files


def average_over_period(da, frequency):
    """
    Calculate average over a period, adjusted by frequency.

    Parameters:
        da (xr.DataArray): DataArray with a time dimension
        frequency (str): Frequency code ('YS', 'QS-DEC', 'MS', etc.)

    Returns:
        xr.DataArray: Averaged data
    """

    if frequency == 'YS':
        da_mean = da.mean(dim="time")
    else:
        da_mean = _group_over_period(da, frequency).mean(dim="time")

    return da_mean


def anomaly_over_period(da: xr.DataArray,
                        da_ref: xr.DataArray,
                        frequency: str,
                        percentage: bool = False) -> xr.DataArray:
    """
    Calculate anomalies between `da` and `da_ref` over a given frequency.

    Parameters
    ----------
    da : xr.DataArray
        Input data (e.g., target period).
    da_ref : xr.DataArray
        Reference data.
    frequency : str
        Frequency string, e.g. 'YS', 'QS-DEC', 'MS'.
    percentage : bool, optional
        If True, compute percentage anomalies. Default is False (absolute
    anomalies).

    Returns
    -------
    xr.DataArray
        Anomaly values grouped by the specified frequency.
    """

    # Get group labels for da and reference
    if frequency == 'YS':
        # No need to group
        ref_mean = da_ref.mean(dim="time")
        anomaly = da - ref_mean
    else:
        da_grouped = _group_over_period(da, frequency)
        ref_grouped = _group_over_period(da_ref, frequency)
        ref_mean = ref_grouped.mean(dim="time")

        # Align time dimension names if needed
        anomaly = da_grouped - ref_mean
        anomaly = anomaly.reset_coords(_get_groupby_attr(frequency),
                                       drop=True)

    if percentage:
        anomaly = anomaly / ref_mean * 100

    return anomaly


def significance_mask(reference, comparison, freq="YS", alpha=0.05):
    """
    Perform Welch's t-test between a reference dataset and a comparison dataset
    for each group defined by freq, returning only a boolean significance mask.

    Parameters
    ----------
    reference : xr.DataArray
        Reference period data (baseline). Must have a 'time' dimension.
    comparison : xr.DataArray
        Dataset to compare against the reference. Must have a 'time' dimension.
    freq : str
        Pandas-style frequency string ('YS' = yearly, 'QS-DEC' = seasonal, 'MS'
    = monthly).
    alpha : float
        Significance level.

    Returns
    -------
    sig_mask : xr.DataArray
        Boolean mask where the difference is significant, indexed by grouped
        time.
    """

    import xarray as xr
    from scipy.stats import ttest_ind

    def ttest_func(a, b):
        _, pvals = ttest_ind(a, b, axis=0, equal_var=False, nan_policy="omit")
        return pvals < alpha  # directly return boolean

    # Get spatial coordinates
    dims = [d for d in reference.dims if d != 'time']
    coords = {d: reference.coords[d] for d in dims}

    if _get_groupby_attr(freq) == "year":
        # Direct test without grouping
        sig_mask = xr.apply_ufunc(
            ttest_func,
            reference.values,
            comparison.values,
            input_core_dims=[["time"], ["time"]],
            output_core_dims=[[]],
            dask="parallelized",
            output_dtypes=[bool]
        )

        # Create DataArray for this group with spatial coordinates
        sig_da = xr.DataArray(sig_mask, dims=dims, coords=coords)
    else:
        # Normal grouped processing for month/season
        sig_masks = []
        ref_grouped = _group_over_period(reference, freq)
        cmp_grouped = _group_over_period(comparison, freq)

        for key, group in ref_grouped:
            ref_grp = ref_grouped[key]
            cmp_grp = cmp_grouped[key]
            # @future HR
            # Somehow reset the time coordinate here to avoid using values.
            sig_mask = xr.apply_ufunc(
                ttest_func,
                ref_grp.values,
                cmp_grp.values,
                input_core_dims=[["time"], ["time"]],
                output_core_dims=[[]],
                dask="parallelized",
                output_dtypes=[bool]
            )

            # Add a temporary 'time' coordinate for the group key
            coords['time'] = [key]

            sig_da = xr.DataArray(sig_mask[None, ...],
                                  dims=['time']+dims,
                                  coords={'time': [key], **coords})
            sig_masks.append(sig_da)

        # Combine all groups along new time dimension
        sig_da = xr.concat(sig_masks, dim='time')

    if freq.startswith("QS"):
        # Reorder season
        season_order = ["DJF", "MAM", "JJA", "SON"]
        sig_da = sig_da.reindex(time=season_order)

    return sig_da


def _group_over_period(da, frequency):

    """
    Group DataArray over a period by a given frequency.

    Parameters:
        da (xr.DataArray): DataArray with a time dimension
        frequency (str): Frequency code ('YS', 'QS-DEC', 'MS', etc.)

    Returns:
        xr.DataArray: Grouped data
    """

    # Group by the given frequency and average each group
    return da.groupby(f"time.{_get_groupby_attr(frequency)}")


def _get_groupby_attr(freq):
    """
    Helper to get the appropriate groupby attribute from a frequency string.
    """
    if freq.startswith("MS"):
        return "month"
    elif freq.startswith("QS"):
        return "season"
    elif freq.startswith("YS"):
        return "year"
    else:
        raise ValueError(f"Unsupported frequency: {freq}")


def get_output_frequency(freq, average=None, anomaly=None):
    """
    Determines the appropriate output frequency string based on input `freq`
    and optional 'average' or 'anomaly' flags.

    Args:
        freq (str): The input frequency string (e.g., 'YS', 'MS').
            The part before the hyphen must be a valid key.
        average (bool, optional): If True, indicates an average
            calculation. Defaults to False.
        anomaly (str, optional): If True, indicates an anomaly
            calculation. Defaults to False.

    Returns:
        str: The processed output frequency string (e.g., 'yr', 'monC').

    Raises:
        KeyError: If the base frequency part of 'freq' is not recognized.
    """

    output_frequencies = {'YS': 'yr', 'MS': 'mon', 'QS': 'sem'}
    base_freq_key = freq.split('-')[0]
    ofreq = output_frequencies.get(base_freq_key, base_freq_key)

    # Add climatology letter "C"
    if average:
        ofreq = ofreq+'C'

    # Set time steps and time bounds for seasonal data
    #

    return ofreq


def create_dataset(result, var_attrs, global_attrs,
                   thresholds=None, durations=None, significance=None):

    """
    Combines a climate indicator xarray DataArray with additional DataArrays
    (thresholds, durations) into a single xarray Dataset, applying
    variable-specific and global attributes.

    This function first updates the attributes of the `result` DataArray with
    `var_attrs`, then converts `result` into a Dataset. It then iteratively
    adds DataArrays generated from `thresholds` and `durations` lists as new
    variables to the Dataset. Finally, it applies `global_attrs` to the entire
    Dataset.

    Args:
        result (xr.DataArray): The primary xarray DataArray that will form the
            main data variable of the new Dataset. Its attributes will be
            updated by `var_attrs`.
        var_attrs (dict): A dictionary of attributes to be added or updated on
            the `result` DataArray. These become attributes of the
            corresponding variable in the output Dataset.
        global_attrs (dict): A dictionary of attributes to be added or updated
            as global metadata for the entire xarray Dataset.
        thresholds (list, optional): A list of objects, each expected to have a
            `.to_xarray()` method that returns an `xarray.DataArray`. Each
            returned DataArray will be added as a new variable to the Dataset,
            using its `name` attribute as the variable name. Defaults to None.
        durations (list, optional): A list of objects, similar to `thresholds`,
            each expected to have a `.to_xarray()` method. These will also be
            added as new variables to the Dataset. Defaults to None.
        significance (xr.DataArray, optional): A significance mask according to
            the save result xarray DataArray.

    Returns:
        xr.Dataset: An xarray Dataset containing the `result` DataArray as its
                    primary variable, along with any additional variables from
                    `thresholds` and `durations`, and all specified attributes.

    Note:
        The `result` DataArray's attributes are updated in-place by `var_attrs`
        before it is converted to a Dataset.
    """

    result.attrs.update(var_attrs)

    ds = result.to_dataset()

    if thresholds:
        for thres in thresholds:
            thres_array = thres.to_xarray()
            ds[thres_array.name] = thres_array

    if durations:
        for dur in durations:
            dur_array = dur.to_xarray()
            ds[dur_array.name] = dur_array

    if significance is not None:
        ds['significance_mask'] = significance

    ds.attrs.update(global_attrs)

    return ds


def set_time_labels_and_bounds(ds, ofreq, start_date, end_date):

    """
     Assign time coordinates and climatology bounds to a Dataset based on
     output frequency and date range.

    Parameters
    ----------
    ds : xarray.Dataset
        The dataset for which to assign time labels and optionally
        climatological bounds. It may have scalar or missing time dimensions,
        or use alternate dimensions like 'month' or 'season'.
    ofreq : str
        Output frequency code:
        - 'yr', 'mon', 'sem' for standard time series (single-point or
        multi-point) where time bounds can be inferred.
        - 'yrC', 'monC', 'semC' for climatological aggregations, where the time
        coordinate represents a centered period.
    start_date : str
        Start date of the analysis period in 'YYYYMMDD' format.
    end_date : str
        End date of the analysis period in 'YYYYMMDD' format.

    Returns
    -------
    xarray.Dataset
        The input dataset with updated `time` coordinate(s), and where
        applicable, a `climatology_bounds` variable and `climatology` attribute
        on the time coordinate.

    Notes
    -----
    - For `yrC`, the time is set to July 1 of the midpoint year.
    - For `semC`, the midpoint dates are set for DJF, MAM, JJA, SON if present
        in `ds['season']`.
    - For `monC`, each month's midpoint is used (e.g., 15th of each month) if
        present in `ds['month']`.
    - In climatological modes (`*C`), a `climatology_bounds` variable is added
        with `time` as the primary dimension.
    """

    import pandas as pd
    import numpy as np

    from pyku.timekit import set_time_bounds_from_time_labels
    from pyku.timekit import set_time_labels_from_time_bounds

    # Convert to pandas datetime
    start_date = pd.to_datetime(start_date, format='%Y%m%d')
    end_date = pd.to_datetime(end_date, format='%Y%m%d')

    if ofreq in ['yr', 'mon', 'sem']:
        # This part handles timeseries of indicators
        if len(ds.time) == 1:
            # Compute midpoint
            midpoint = np.datetime64(start_date +
                                     (end_date - start_date) / 2)

            # Case 1: If 'time' is a scalar coordinate
            if "time" in ds.coords and "time" not in ds.sizes:
                ds = ds.drop_vars("time")
                ds = ds.expand_dims(time=[midpoint])
            # If 'time' is a dimension
            elif "time" in ds.sizes:
                # Replace with length-1 dimension
                ds = ds.isel(time=0).expand_dims(time=[midpoint])

            # If 'time' does not exist at all
            else:
                ds = ds.expand_dims(time=[midpoint])
        else:
            ds = set_time_bounds_from_time_labels(ds)
            ds = set_time_labels_from_time_bounds(ds, how='middle')
    elif ofreq in ['yrC', 'semC', 'monC']:
        # This section handles climatological indicator statistics

        start_year = start_date.year
        end_year = end_date.year
        mid_year = (start_year + end_year) // 2

        if ofreq == "yrC":
            ds = ds.expand_dims(time=[np.datetime64(f"{mid_year}-07-01")])

        elif ofreq == "semC":
            # Full seasonal mapping with DJF first
            season_labels = ["DJF", "MAM", "JJA", "SON"]
            season_dates = {
                "DJF": np.datetime64(f"{mid_year}-01-16"),
                "MAM": np.datetime64(f"{mid_year}-04-16"),
                "JJA": np.datetime64(f"{mid_year}-07-16"),
                "SON": np.datetime64(f"{mid_year}-10-16"),
            }

            # Detect which seasons are in the dataset
            if "season" not in ds.coords:
                raise ValueError("""Dataset must have a 'season' coordinate for
                'semC' frequency.""")
            seasons_present = list(ds.coords["season"].values)
            ordered_seasons = [s for s in season_labels
                               if s in seasons_present]
            times = [season_dates[s] for s in ordered_seasons]

            # Assign time and reorder dataset
            ds = ds.sel(season=ordered_seasons)
            ds = ds.assign_coords(time=("season", times))
            ds = ds.swap_dims({"season": "time"})
            ds = ds.sortby("time")
        elif ofreq == "monC":
            month_dates = {i: np.datetime64(f"{mid_year}-{i:02d}-15")
                           for i in range(1, 13)}
            if "month" not in ds.coords:
                raise ValueError("""Dataset must have a 'month' coordinate for
            'monC' frequency.""")
            months_present = list(ds.coords["month"].values)
            ordered_months = sorted(months_present)  # ensure 1–12 order
            times = [month_dates[m] for m in ordered_months]

            # Assign time and reorder dataset
            ds = ds.sel(month=ordered_months)
            ds = ds.assign_coords(time=("month", times))
            ds = ds.swap_dims({"month": "time"})
            ds = ds.drop_vars("month")
            ds = ds.sortby("time")

        # Add climatology time bounds
        ds = set_clim_bnds_labels(ds, ofreq, start_year, end_year)
    else:
        raise ValueError(f"Unsupported frequency: {ofreq}")

    return ds


def set_clim_bnds_labels(
        ds: xr.Dataset, ofreq: str, start_year: int, end_year: int
) -> xr.Dataset:

    """
    Add climatology_bounds variable to dataset based on frequency and start/end
    years.

    Parameters:
        ds (xr.Dataset): Dataset with a time coordinate already assigned.
        ofreq (str): Climatological frequency: 'yrC', 'semC', 'monC'.
        start_year (int): Climatology start year.
        end_year (int): Climatology end year.

    Returns:
        xr.Dataset: Dataset with climatology_bounds variable and updated time
        attributes.
    """

    import numpy as np
    import pandas as pd

    bounds = []

    if ofreq == "yrC":
        start = np.datetime64(f"{start_year}-01-01")
        end = np.datetime64(f"{end_year}-01-01")
        bounds = [[start, end]] * ds.sizes["time"]
    elif ofreq == "semC":
        for t in ds.time.values:
            label = pd.to_datetime(t)
            month = label.month
            if month == 1:  # DJF → Dec(start-1) to Mar(end)
                start = np.datetime64(f"{start_year-1}-12-01")
                end = np.datetime64(f"{end_year}-03-01")
            elif month == 4:  # MAM
                start = np.datetime64(f"{start_year}-03-01")
                end = np.datetime64(f"{end_year}-06-01")
            elif month == 7:  # JJA
                start = np.datetime64(f"{start_year}-06-01")
                end = np.datetime64(f"{end_year}-09-01")
            elif month == 10:  # SON
                start = np.datetime64(f"{start_year}-09-01")
                end = np.datetime64(f"{end_year}-12-01")
            else:
                raise ValueError(f"Unexpected mid-season time label: {label}")
            bounds.append([start, end])
    elif ofreq == "monC":
        for t in ds.time.values:
            label = pd.to_datetime(t)
            m = label.month
            y_start = start_year
            y_end = end_year
            # Handle Dec correctly when next month is Jan
            if m == 12:
                start = np.datetime64(f"{y_start}-{m:02d}-01")
                end = np.datetime64(f"{y_end+1}-01-01")
            else:
                start = np.datetime64(f"{y_start}-{m:02d}-01")
                end = np.datetime64(f"{y_end}-{(m+1):02d}-01")
            bounds.append([start, end])
    else:
        raise ValueError(f"Unsupported frequency: {ofreq}")

    # Create climatology_bounds variable
    clim_bounds = xr.DataArray(
        np.array(bounds, dtype="datetime64[ns]"),
        dims=("time", "nv"),
        coords={"time": ds.time},
        name="climatology_bounds",
    )

    # Add to dataset and link to time
    ds["climatology_bounds"] = clim_bounds
    ds["time"].attrs["climatology"] = "climatology_bounds"

    return ds
