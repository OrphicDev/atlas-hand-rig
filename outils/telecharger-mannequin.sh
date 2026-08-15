#!/usr/bin/env bash
# Le maillage de base est le « Human Base Meshes bundle » de Blender Studio,
# publié en CC0 (domaine public). Il pèse 47 Mo : trop lourd pour être versionné
# ici, et de toute façon inutile pour VÉRIFIER le rig — seul sa CONSTRUCTION en
# a besoin.
#
#   Source : https://studio.blender.org/tools/assets/human-base-meshes
#   Licence : CC0
#   Version employée : human-base-meshes-bundle-v1.4.1
#
# Une fois téléchargé, désignez le fichier .blend :
#   export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend
set -eu
echo "Téléchargez le bundle CC0 depuis :"
echo "  https://studio.blender.org/tools/assets/human-base-meshes"
echo "puis :"
echo "  export ATLAS_BASE_MESH=/chemin/vers/human_base_meshes_bundle.blend"
