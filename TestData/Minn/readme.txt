This readme.txt file was generated on 20151130 by Zhuozhi Georgia Huang

GENERAL INFORMATION

1. Title of Dataset: 2011 Rock Properties Database: Density, Magnetic Susceptibility, and Natural Remanent Magnetization of Rocks in Minnesota
2. File Information:
   A. Filename: rock_prop2011.zip
   B. Short description: Rock Properties Database 2011
   C. Filename: Rock_Prop_report_2011.pdf
   D. Short description: Report and Database description
   E. Filename: rock_prop2011_archive.zip
   F. Short description: Archival Version of Rock Properties Database 2011
   G. If data set includes multiple files related to one another, include relationship here: 
      i. Rock_Prop_report_2011.pdf describes the database and highlights the upgrade from its first version (Rock Properties Database 2003). 
      ii. rock_prop2011_archive.zip contains the .csv version of the three tables in the database and a Entity Relationship Diagram describing the database structure. 

3. Principal Investigator Contact Information
   A. Name:Chandler V.W.
   B. Institution:University of Minnesota Twin Cities
   C. Address:Minnesota Geological Survey, 2609 Territorial Rd, Saint Paul, MN 55114-1009
   D. Email:chand004@umn.edu

4. Associate or Co-investigator Contact Information
   A. Name:Lively, R.S.
   B. Institution:University of Minnesota Twin Cities
   C. Address:Minnesota Geological Survey, 2609 Territorial Rd, Saint Paul, MN 55114-1009
   D. Email:lively@umn.edu

5. Group Contact Information
   A: Name: Minnesota Geological Survey
   B: Institution: University of Minnesota Twin Cities
   C. Address:Minnesota Geological Survey, 2609 Territorial Rd, Saint Paul, MN 55114-1009
   D. Email: mgs@umn.edu

6. Date of data collection (single date, range, approximate date): The database was upgraded during the period between 2009 and 2011. 

7. Geographic location of data collection (where was data collected?): Most data are collected in Minnesota. Some seismic velocity data are collected in western Wisconsin. A group of Paleozoic samples are collected in Iowa. 

8. Date files were created: 20151119

9. Are there multiple versions of the dataset? yes
   A. If yes, list versions: This is Version 2.0 of the Minnesota Geological Survey Rock Properties Database
   B. Name of file that was updated: The 2011 Rock Properties Database (rock_prop2011.zip) updates the 2003 Rock Properties Database (rock_properties.dbf). 
      i. Why was the file updated? A project was initiated in 2009 to upgrade the rock properties database by providing a format that could incorporate vertically-referenced samples from drill core, add readily available density and magnetic susceptibility data from core into the database, and allow a straightforward addition of core log data in the future. We also incorporated new, single point, surface-referenced data that were acquired during Minnesota Geological Survey projects since 2003. Some data were also recovered from older projects that had been missed by early compilation. Overall, the upgraded database features the addition of Drill Core Data, the addition of new surface-referenced(X,Y) data, and the addition of density inferred from seismic velocity data.  
      ii. When was the file updated? between 2009 and 2011


10. Information about funding sources that supported the collection of the data:
Acquisition of data in the 1950’s was funded by the University of Minnesota and the U. S. Geological Survey. Acquisition from 1979 to 1984 was supported by the Aeromagnetic Survey Program of the Minnesota Geological Survey, which was funded by the Minnesota Legislature as recommended by the Legislative Commission on Minnesota Resources. Additional legislative support was provided through the Minerals Coordinating Committee and the State Special Appropriation for the Minnesota Geological Survey. Support since 1984 has been provided through the U. S. Geological Survey (COGEOMAP and STATEMAP projects), and the MGS-MNDNR County Geologic Atlas Program. Finally, the legislative support for this upgrade as recommended by the Minnesota Mineral Coordinating Committee and managed through MNDNR is greatly appreciated.


METHODOLOGICAL INFORMATION

1. Description of methods used for collection/generation of data: 
   A. The drill core dataset was derived from notebooks and other files at the Minnesota Geological Survey (MGS), drillcore information from partner agencies, and, in a few cases, new readings on core stored at either the MGS and Minnesota and Minnesota Department of Natural Resources. 
   B. Density data for sedimentary rocks were estimated using P-wave velocities derived from seismic refraction surveys carried out in Minnesota and western Wisconsin over the past several decades. The computations were done using formulas inferred from empirical relationships 
   C. New surface-referenced data were complied from the backlog of rock property data from in-situ and hand samples. These rock property data were collected to facilitate interpretation of the gravity and magnetic detail in the Tower-Soudan area of NE Minnesota. 


2. Instrument-specific information needed to interpret the data:
The rock properties database was created as part of a project file (mxd) in ArcGis 10. However, the specific shapefile and database tables that hold the data can be read by any version of ArcGis. No ArcGis extensions are needed. To view the data spatially, double click the project file (RP2011.mxd) in the zip file, which opens ArcMap (one program of ArcGIS) if it is installed on the computer and the files will load as part of the project. Users can also open the file from within ArcMap if ArcMap is already running. The outlines for Minnesota counties are included for users’ convenience. The Add Data tool in ArcMap allows users to add the database to another mxd project, but the dbf relationships for the secondary tables will not be available as they are part of RP2011.mxd.  


3. Describe any quality-assurance procedures performed on the data:
   A. Density (the value in field DENSITY_SI) was determined in two different ways according to the value in the TYPE field. 
   B. When determining the magnetic susceptibility (the value in field MAG_SUS_SI), corrections have been made for estimated air space (chip sample) and sample dimension, in accordance with recommendation given by the manufacturers of a particular instrument. 
   C. If the magnetic susceptibility is non-zero, but too weak to be properly determined by the device used, the MAG_SUS_LT field is used to indicate that the magnetic susceptibility is less than a certain value. 
   D. Most sedimentary rocks are porous and poorly consolidated, making them unsuited for the classical density measurement technique. Empirical relationships have been developed that estimate a sediment’s density using P-wave velocities derived from seismic refraction surveys. 
 

4. Codes or symbols used to note or characterize low quality/questionable outliers that people should be aware of:
Locations that are thought to be in error of 400 meters or more are annotated in either the COMMENTS or COMMENT2 field.
 

5. People involved with sample collection, processing, analysis and/or submission:
Many individuals have contributed to the rock properties database over the years. Charles Jahren generously provided the notes, data, and samples that he and Gordon Bath used in their studies during the 1950's. Professors Myrl E. Beck, Jr. (Western Washington University) and H. Currie Palmer (The University of Western Ontario) generously provided field materials and other information from their own studies. Professor John C. Green (University of Minnesota, Duluth) provided unpublished paleomagnetic data from studies by Kenneth G. Books and others. For more information, please reference the citation section below. 

In addition to those individuals named in the citation section, others who have assisted at various times with the MGS data include, Laura Beauchane, Terri Haake, Lisa Kivaekas, Angela McGowan, Peter McSwiggen, Sahu Sanghamitra, Bryan Schaap and Dale Setterholm. During the summer of 2010 Roger Morrison lent valuable assistance during the early stages this compilation. Finally, the authors wish to give a special thanks to Jack Barland who worked on the project as a student during 2010-2011. Jack’s efforts spanned data acquisition through GIS compilation, and his skills as a quick learner and a diligently consistent worker added much to the success of the program.

6. citation
Bath, G. D., 1962, Magnetic anomalies and magnetizations of the Biwabik Iron Formation, Mesabi Area, Minnesota: Geophysics, v. 27, number 5, p. 627-650.Beck, M. E., 1970, Paleomagnetism of Keweenawan intrusive rocks, Minnesota, Journal of Geophysical Research, v. 75, p. 4985-4996.Beck, M. E., and Lindsley, N. C., 1969, Paleomagnetism of the Beaver Bay Complex, Minnesota: Journal of Geophysical Research, v. 74, p. 2002-2013.Bleifuss, R. L., 1952, Correlation of magnetite content with magnetic susceptibility measurements of Minnesota Precambrian rocks: University of Minnesota, M.S. thesis, 46 p.

Books, K. G., 1972, Paleomagnetism of some Lake Superior Keweenawan rocks: U. S. Geological Survey Professional Paper 760, 42 p.
Brocher, T. M., 2005, Compressional and Shear Wave Velocity Versus Depth in the San Francisco Bay Area, California: Rules for USGS Bay Area Velocity Model 05.0.0, U. S. Geological Survey Open-File Report 05–13172005
Chandler, V.W., 1994, Gravity Investigation for Potential Ground-Water Resources in Rock County, Minnesota, Minnesota Geological Survey, Report of Investigations, RI-44, 24 p.Chandler, V. W., 1991, Aeromagnetic anomaly map of Minnesota: Minnesota Geological Survey, State Map Series, S-17, Scale 1:500,000.
Chandler, V. W., and Schaap, B. D., 1991, Bouguer gravity anomaly map of Minnesota: Minnesota Geological Survey, State Map Series, S-18, Scale 1:500,000.
Chandler, V.W., Jirsa, M.A., and Boerboom, T.J., 2008, A gravity and magnetic investigation of east-central Minnesota: Insights into the structure and evolution of the Paleoproterozoic Penokean Orogen, Minnesota Geological Survey, Report of Investigations, RI-66, 33 p.

DuBois, P. M., 1962, Paleomagnetism and correlation of Keweenawan rocks: Geological Survey of Canada Bulletin 71, 75 p.Fogelson, D. E., 1956, A gravity survey of Redwood County, Minnesota, University of Minnesota, unpublished M.S. thesis, 40 p.Grout, Frank F. and Wolff, J. F. Sr., 1955, The geology of the Cuyuna District, Minnesota, A progress report, Minnesota Geological Survey, Bulletin 36, 144 p.Gardner, G. H. F., Gardner L. W., and Gregory, A. R., 1974, Formation velocity and density—the diagnostic basics for stratigraphic traps, Geophysics 39, p. 770-780.Jahren, C. E., 1965, Magnetization of Keweenawan rocks near Duluth, Minnesota, Geophysics, v. 30, p. 858-874.Jirsa, M. A., Boerboom, T. J., Chandler, V. W., Mossler, J. H., Runkel, A. C., and Setterholm, D. R., 2011, Geologic map of Minnesota, Bedrock Geology, Minnesota Geological Survey, State Map Series, S-21, Scale 1:500,000.Mooney H.M. and Bleifuss, R. L. 1953, Magnetic susceptibility measurements in Minnesota-Part 3, analysis of field results. Geophysics, v. 18, p. 383-393.

Mooney, H.M., Farnham, P.R., Johnson, S.H., Wolz, G. and Craddock, C., 1970, Seismic Studies Over the Midcontinent Gravity High in Minnesota and Northwestern Wisconsin, Minnesota Geological Survey, Report of Investigations, RI-11, 191 p.Palmer, H. C., 1970, Paleomagnetism and correlation of some middle Keweenawan rocks, Lake Superior, Canadian Journal of Earth Sciences, v. 7, p. 1410-1436.


DATA-SPECIFIC INFORMATION

1. Description of Database Parameters/Column headings for tabular data:
   A. Full name: RELATEID
   B. Definition: This field contains a unique, sequential number for each entry within the database. The number is not correlative to specific sample types or data order. Its main function is to provide a unique link to secondary data tables. 
   C. Full name: SAMPLEID
   D. Definition: This field contains the sample or field number as assigned by the original collector. This is commonly alpha-numeric and is not consistent within the database. Although the same sample number could exist for different samples, it is not common. 
   E. Full name: TYPE
   F. Definition: This field describes the type of sample used for this particular entry and can be Sample (refers to measurements based on outcrop or a hand sample), Drillcore (refers to measurements based on a discrete piece of core), Site (contains properties based on average values of samples at a discrete site), or Seismic (contains density values estimated from seismic velocity data). 
   G. Full name: TYPE_MOD (TYPE_MODIFIER)
   H. Definition: This field contains a modifier to the TYPE field that allows the Drillcore sample type to be separated into those with down-hole data and those without.
   I. Full name: MAJOR_DIV (MAJOR_DIVISION)
   J. Definition: This field contains information about the geologic association of the sample on the scale of an orogen or subprovince. 
   K. Full name: MINOR_DIV (MINOR_DIVISION)
   L. Definition: This field refers to a large map unit, usually a major geologic body or a rock formation. 
   M. Full name: SUB_DIV (SUB_DIVISION)
   N. Definition: This field allows for further geologic division wherever necessary,usually refers to a local rock unit or body. 
   O. Full name: ROCK_TYPE
   P. Definition: This field contains a very general description of the sample as given by the collector, and does not conform to any particular rock classification scheme. 
   Q. Full name: DENSITY_SI
   R. Definition: This field gives density in SI units. The density was determined in two different ways depending on the value in the TYPE field. 
   S. Full name: MAG_SUS_SI (MAGNETIC_SUSCEPTIBILITY_SI)
   T. Definition: This filed gives magnetic susceptibility in SI units. 
   U. Full name: MAG_SUS_LT (MAGNETIC_SUSCEPTIBILITY_LESS THAN)
   V. Definition: This field means that the magnetic susceptibility is less than the value given here. 
   W. Full name: CITATION
   X. Definition: This field credits the individuals who acquired the data. It two names are given, the first designates who was responsible for field collection, and the second designates who did the laboratory measurements. 
   Y. Full name: ACQ_DATE (ACQUISITION_DATE)
   Z. Definition: This field provides the estimated date of acquisition, as available. 
   a. Full name: MAG_METHOD (MAGNETIC_METHOD)
   b. Definition: This field describes the methodology and instrumentation used for magnetic susceptibility measurements. Where applicable, this field may also specify whether an astatic magnetometer or a spinner magnetometer was used for natural remanent magnetization measurements. Measurements of natural remanent magnetization without any specification in this field were made at Minnesota Geological Survey using a Schondstedt Model SSM-1 spinner magnetometer. 
   c. Full name: COMMENTS
   d. Definition: This field provides supplemental information on a given sample. In some cases it presents additional geologic information. In others it provides more details about the precision of the determination or its location. 
   e. Full name: NUM_SAM (NUMBER_SAMPLE)
   f. Definition: This field descries the number of samples used, if known. 
   g. Full name: J_NRM
   h. Definition: This field provides the intensity of natural remanent magnetization in SI units. 
   i. Full name: DEC_NRM (DECLINATION_NATURAL REMANENT MAGNETIZATION)
   j. Definition: This field provides the declination of natural remanent magnetization in degrees. 
   k. Full name: INC_NRM (INCLINATION_NATURAL REMANENT MAGNETIZATION)
   l. Definition: This field provides the inclination of natural remanent magnetization in degrees.
   m. Full name: POLARITY
   n. Definition: This field provides the natural remanent magnetization polarity as N (normal or downward directed) or R (reversed or upward directed), and is given where no other natural remanent magnetization data are available. 
   o. Full name: GEO_STRIKE
   p. Definition: strike of structural correction applied to the natural remanent magnetization data. If blank, no structural correction has been applied. 
   q. Full name: GEO_DIO
   r. Definition: dip of structural correction applied to the natural remanent magnetization data. If blank, no structural correction has been applied. 
   s. Full name: POINT_X
   t. Definition: UTM easting (meters) NAD83, Zone 15N
   u. Full name: POINT_Y
   v. Definition: UTM northing (meters) NAD83, Zone 15N
   w. Full name: S_ELEV_FT (SURFACE_ELEVATION_FEET)
   x. Definition: This field provides Surface elevation in feet relative to mean sea level, inferred from the 30 meter DEM (Digital Elevation Model) grid of the U.S. Geological Survey. Values of -999 indicates points outside the boundary of the Minnesota DEM. 
   y. Full name: TIME_DIV (TIME_DIVISION)
   z. Definition: Gross time division of rock unit, as inferred by geo-referencing point locations to S21, the published state bedrock map of Minnesota (Jirsa and others, 2011)
   A1. Full name: COMMENTS2
   B1. Definition: The field provides additional comments, if needed.

2. Units of measurements: 
Values of rock density, magnetic susceptibility and natural remanent magnetization are given in SI units (International System of Units, i.e. meter, kilogram, seconds), as apposed to the older c.g.s. units (centimeter, gram, seconds). S_ELEV_FT is measured in feet. 


3. Codes or symbols used to record missing data
   A. Code/symbol: -999
   B. Definition: Missing data or no data in the numeric fields. -999 in the S_ELEV_FT field refers to points outside the boundary of the Minnesota DEM (Digital Elevation Model). 
   C. Code/symbol:  left as blank space
   D. Definition: Missing data or no data in the text fields


SHARING/ACCESS INFORMATION 

1. Links to publications that cite or use the data:
Chandler, V.W; Lively, R.S.(2011). Density, Magnetic Susceptibility, and Natural Remanent Magnetization of Rocks in Minnesota: An MGS Rock Properties Database. Minnesota Geological Survey. Retrieved from the University of Minnesota Digital Conservancy, http://hdl.handle.net/11299/175580

2. Links to other publicly accessible locations of the data:
You may find the interactive GIS database at  
http://mgsweb2.mngs.umn.edu/MgsRockProperties/


3. Recommended citation for the data:
Chandler, V.W; Lively, R.S. (2015). 2011 Rock Properties Database: Density, Magnetic Susceptibility, and Natural Remanent Magnetization of Rocks in Minnesota [dataset]. Retrieved from the Data Repository for the University of Minnesota, http://dx.doi.org/10.13020/D63S3D.


Credits: Template provided by the University of Minnesota Libraries, http://lib.umn.edu/datamanagement
