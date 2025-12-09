import bpy
import ifcopenshell
import ifcopenshell.util.element as ifc_elem
from blenderbim.bim.ifc import IfcStore

ifc = IfcStore.get_file()
if not ifc:
    raise RuntimeError("Nenhum arquivo IFC ativo no BlenderBIM (IfcStore.get_file() retornou None).")

def safe_get_psets(e):
    """Compatível com versões antigas e novas do IfcOpenShell."""
    try:
        return ifc_elem.get_psets(e, include_inherited=True) or {}
    except TypeError:
        return ifc_elem.get_psets(e) or {}

def material_to_name(m):
    """Converte várias formas de material IFC em um nome amigável."""
    if not m:
        return None
    t = m.is_a()
    if t == "IfcMaterial":
        return m.Name or None
    if t == "IfcMaterialLayerSetUsage":
        layers = getattr(m.ForLayerSet, "MaterialLayers", []) or []
        names = [ly.Material.Name for ly in layers
                 if getattr(ly, "Material", None) and getattr(ly.Material, "Name", None)]
        return ", ".join(names) or None
    if t == "IfcMaterialLayerSet":
        layers = getattr(m, "MaterialLayers", []) or []
        names = [ly.Material.Name for ly in layers
                 if getattr(ly, "Material", None) and getattr(ly.Material, "Name", None)]
        return ", ".join(names) or None
    if t == "IfcMaterialList":
        mats = getattr(m, "Materials", []) or []
        names = [mm.Name for mm in mats if getattr(mm, "Name", None)]
        return ", ".join(names) or None
    if t == "IfcMaterialConstituentSet":
        consts = getattr(m, "MaterialConstituents", []) or []
        names = [c.Material.Name for c in consts
                 if getattr(c, "Material", None) and getattr(c.Material, "Name", None)]
        return ", ".join(names) or None
    if t == "IfcMaterialProfileSet":
        profs = getattr(m, "MaterialProfiles", []) or []
        names = [p.Material.Name for p in profs
                 if getattr(p, "Material", None) and getattr(p.Material, "Name", None)]
        return ", ".join(names) or None
    return t  # fallback: tipo da entidade

for obj in bpy.context.scene.objects:
    # Os objetos importados pelo BlenderBIM normalmente têm esse property group
    if hasattr(obj, "BIMObjectProperties"):
        ifc_id = getattr(obj.BIMObjectProperties, "ifc_definition_id", None)
        if not ifc_id:
            continue

        # by_id geralmente espera int; alguns builds aceitam str, mas vamos garantir
        try:
            ent = ifc.by_id(int(ifc_id))
        except Exception:
            ent = ifc.by_id(ifc_id)

        if not ent:
            continue

        print("\nObjeto Blender:", obj.name)

        # Atributos básicos
        ifc_class = ent.is_a()
        guid = getattr(ent, "GlobalId", "")
        name = getattr(ent, "Name", "") or ""
        obj_type = getattr(ent, "ObjectType", None)
        tag = getattr(ent, "Tag", None)

        print("  IFC Class:", ifc_class)
        print("  GlobalId:", guid)
        print("  Name:", name)
        print("  ObjectType:", obj_type)
        print("  Tag:", tag)

        obj["ifc_class"] = ifc_class
        obj["ifc_guid"] = guid
        obj["ifc_name"] = name
        obj["ifc_ObjectType"] = obj_type if obj_type is not None else ""
        obj["ifc_Tag"] = tag if tag is not None else ""

        # --- MATERIAIS (pela relação IFC, não por Pset) ---
        mat_entity = ifc_elem.get_material(ent)
        obj["ifc_material"] = material_to_name(mat_entity) or "Sem material"

        # --- PSETS (agora sim calculamos antes de usar) ---
        psets = safe_get_psets(ent)

        # Alguns exportadores (Revit) colocam material estrutural em "Materials and Finishes / Structural Material"
        # Faça um fallback para outros nomes comuns se necessário.
        structural_mat = None
        mf = psets.get("Materials and Finishes", {}) or {}
        structural_mat = mf.get("Structural Material")

        if structural_mat is None:
            # Tentar no TYPE
            typ = ifc_elem.get_type(ent)
            if typ:
                psets_t = safe_get_psets(typ)
                mf_t = psets_t.get("Materials and Finishes", {}) or {}
                structural_mat = mf_t.get("Structural Material")

        obj["ifc_structural_material"] = structural_mat or ""

        print("  IFC material (entidade):", obj["ifc_material"])
        print("  Structural Material (Pset):", obj["ifc_structural_material"])