"""
Zone, Region, and Division hierarchy for dependent dropdowns
"""

ZONE_STRUCTURE = {
    "Central-Western Zone": {
        "Tarkwa": ["Tarkwa div", "Enchi", "Asankragua"],
        "Takoradi": ["Takoradi div", "Axim", "Half Assini"],
        "Cape Coast": ["Cape Coast div", "Swedru", "Assin Fosu", "Mankessim", "Winneba", "Elmina", "Asikuma"]
    },
    "Greater Accra Zone": {
        "Accra Metro": ["Abeka-Lapaz", "Ablekuma", "Accra New Town", "Adabraka", "Dansoman", "Odorkor", "Laterbiokorshie", "Anyaa", "La-Osu"],
        "Kasoa": ["Kasoa", "Weija"],
        "Madina": ["Madina div"],
        "Tema": ["Tema div", "Ashaiman", "Teshie-Nungua", "Ada"],
        "Ga Central": ["Ga-Central div", "Nsawam", "Amasaman"]
    },
    "Ashanti Zone A": {
        "Bibiani": ["Bibiani div", "Wiawso", "Essam Debiso"],
        "Kumasi South": ["Kumasi South div", "Bohyen"],
        "Obuasi": ["Obuasi div", "Dunkwa", "Bekwai", "Subin", "New Edubiase"],
        "Nkawie": ["Nkawie div", "Mankranso"]
    },
    "Ashanti Zone B": {
        "Kumasi North": ["Kumasi North div", "Offinso", "Asokore Mampong"],
        "Mampong": ["Mampong div", "Atebubu", "Effiduase", "Ejura"],
        "Konongo": ["Konongo div", "Agogo", "Juaso", "Ejisu"]
    },
    "Middle Belt Zone": {
        "Sunyani": ["Sunyani div", "Dormaa Ahenkro", "Berekum", "Bechem", "Sampa"],
        "Techiman": ["Techiman div", "Kintampo", "Wenchi", "Nkoranza"],
        "Goaso": ["Goaso div", "Mim", "Kenyase", "Tepa"]
    },
    "Eastern-Volta Zone": {
        "Koforidua": ["Koforidua div", "Akropong", "Suhum", "Odumase"],
        "Akim Oda": ["Akim Oda div", "Donkorkrom", "Nkawkaw", "Asamankese"],
        "Ho": ["Ho div", "Akatsi", "Keta", "Aflao"],
        "Hohoe": ["Hohoe div", "Kpando"],
        "Dambai": ["Dambai div", "Nkwanta", "Krachi"]
    },
    "Northern Zone": {
        "Bolga": ["Bolga div", "Bawku", "Navrongo"],
        "Nalerigu": ["Nalerigu div", "Walewale"],
        "Wa": ["Wa div", "Tumu"],
        "Damango": ["Damango div", "Buipe", "Bole"],
        "Tamale": ["Tamale div", "Yendi", "Salaga"]
    }
}

def get_all_zones():
    """Return list of all zones"""
    return list(ZONE_STRUCTURE.keys())

def get_regions_by_zone(zone):
    """Return regions for a specific zone"""
    return list(ZONE_STRUCTURE.get(zone, {}).keys())

def get_divisions_by_region(zone, region):
    """Return divisions for a specific region within a zone"""
    return ZONE_STRUCTURE.get(zone, {}).get(region, [])