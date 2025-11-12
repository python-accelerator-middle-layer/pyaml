import at
ring = at.load_lattice("config/sr/lattices/ebs.mat")



def prepare_and_save():

    # Remove non standard field
    # Add cell number to FamName
    for e in ring:
        attrs = e.__dict__
        toremove = [k for k,v in attrs.items() if k.startswith('Calibration') or k=="SerialNumber"]
        for tr in toremove:
            delattr(e,tr)
        if hasattr(e,"Device") and not isinstance(e,at.Monitor):
            field = e.Device.split(sep='/')
            cell = field[2].split(sep='-')
            CELL = cell[0].upper()
            e.FamName += f"-{CELL}"
        if hasattr(e,"Device"):
            delattr(e,"Device")

    at.save_lattice(ring,"config/sr/lattices/ebs_jlp.mat")

def dump():
    # Dump lattice 
    for e in ring:
        if e.FamName.startswith("SI"):
            print(e)

dump()