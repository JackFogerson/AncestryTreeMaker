# models.py

class AncestorNode:
    def __init__(self, name, base_ethnicities=None, father=None, mother=None, display_name="", birth_year="", death_year="", is_living=False):
        self.name = name
        self.display_name = display_name if display_name else name
        self.birth_year = birth_year
        self.death_year = death_year
        self.is_living = is_living
        self.base_ethnicities = base_ethnicities if base_ethnicities else []
        self.father = father
        self.mother = mother
        self.computed_ethnicities = {}
