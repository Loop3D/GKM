# Geoscience Knowledge manager

Release 1.0.1 OWL source Dataset in text/ttl files :  [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4743221.svg)](https://zenodo.org/record/4743221)


This repository contains public work items related to development of the ontology and knowledge base for the Loop 3D geology project.

Ontology developed by Boyan M. Brodaric and Stephen M. Richard.

The wiki for this repository contains notes from team meetings. 

Please add issues or comments on the ontology in the issue tracker.


## File:
 - **GSO_v1.0_OFR_8796.pdf**  GSC Open File report describing the ontology [https://doi.org/10.4095/328296](https://doi.org/10.4095/328296)
 - **TimeIntervalRelations.pdf**  Diagram to help clarify Allen temporal relations between intervals and instants.


## Directory:
**Loop3D-GSO** contains the ontology files and associated documentation

### Files: 
 - **GSO-Common.ttl**  OWL file with general framework ontology
 - **GSO-Geology.ttl**  OWL file with framework for geoscience
 - **GSO-Master.ttl**  OWL file that imports all modules to assemble entire GSO ontology

#### Sub directories:
**Modules**  Contains module ontologies building on frameworks in Common and Geology.

**Examples**  Contains a collection of instance documents (the .ttl files) demonstrating representation of various geologic scenarios.  This collection is likely to grow and change over time.

#### other files 
 - **GeologyScenarioForTesting.pptx** (and .pdf) invented cross section that is used for various example documents
 - **EasternRinconMountainsXSec.png** schematic cross section of Eastern Rincon Mountains, Arizona, used for various example documents

test push, try pylode
