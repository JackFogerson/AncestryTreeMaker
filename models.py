# models.py

class AncestorNode:
    def __init__(self, name, base_ethnicities=None, father=None, mother=None):
        self.name = name
        self.base_ethnicities = base_ethnicities if base_ethnicities else []
        self.father = father
        self.mother = mother
        self.computed_ethnicities = {}
