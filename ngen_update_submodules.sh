#!/bin/bash
set -euo pipefail

source config.bashrc

set -x

NGEN_SOURCE_LOCAL=$1

#( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote --recursive )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote test/googletest )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/pybind11 )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/t-route )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/cfe/cfe )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/topmodel/topmodel )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/noah-owp-modular/noah-owp-modular )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/bmi-cxx )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/evapotranspiration/evapotranspiration )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/SoilFreezeThaw/SoilFreezeThaw )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/SoilMoistureProfiles/SoilMoistureProfiles )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/sloth )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/netcdf-cxx4/netcdf-cxx4 )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/LASAM )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/snow17 )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/sac-sma/sac-sma )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/ueb-bmi )
 ( cd ${NGEN_SOURCE_LOCAL}; git submodule update --init --remote extern/lstm )
