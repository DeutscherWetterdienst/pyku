Climatic Regions
================

Climatic regions are defined by the DWD as "natural climatic regions of Germany". 
See https://www.dwd.de/DE/leistungen/klimaprojektionsdaten/pdf/naturraeume.html (German) for more information.


.. ipython::
   :okwarning:

   @savefig pyku_resources_natural_climatic_regions.png width=8in
   In [0]: import pyku
      ...: geodf = pyku.resources.get_geodataframe('natural_climatic_regions_of_germany')
      ...: 
      ...: display(geodf)
      ...: pyku.analyse.regions(geodf, area_def='HYR-GER-LAEA-5', size_inches=(16, 16))
