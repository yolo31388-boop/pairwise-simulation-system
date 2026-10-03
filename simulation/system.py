"""
pairwise-simulation-system - SimulationSystem

A small city-building / management simulation core.

* Income: building revenue + resident consumption + taxes.
* Expenses: building maintenance + worker wages + resource consumption.
* Buildings: position/terrain checks, prerequisites, upgrades.
* Residents: satisfaction, population growth, job assignment.
* Resources: storage caps, production chains, trading.
"""

GRASS = "grass"
WATER = "water"
ROAD = "road"

UNBUILDABLE_TERRAIN = {
    "water", "river", "lake", "sea", "ocean", "pond",
    "road", "street", "highway", "path",
}

BUILDING_ALIASES = {
    "residence": "house",
    "residential": "house",
    "home": "house",
    "store": "shop",
    "commercial": "shop",
    "market": "shop",
    "industrial": "factory",
    "mill": "factory",
}

BUILDING_TYPES = {
    "house": {
        "cost": 100, "maintenance": 2, "jobs": 0, "revenue": 0,
        "housing": 4, "requires": [],
    },
    "farm": {
        "cost": 150, "maintenance": 3, "jobs": 3, "revenue": 10,
        "housing": 0, "requires": [],
        "produces": {"grain": 5},
    },
    "shop": {
        "cost": 200, "maintenance": 5, "jobs": 4, "revenue": 30,
        "housing": 0, "requires": ["house"],
    },
    "factory": {
        "cost": 400, "maintenance": 10, "jobs": 8, "revenue": 0,
        "housing": 0, "requires": ["house"],
        "consumes": {"grain": 2, "wood": 1},
        "produces": {"goods": 3},
    },
}

MAX_LEVEL = 3
RESOURCE_PRICES = {"grain": 2, "wood": 3, "goods": 10}
CONSUMPTION_PER_CAPITA = 2
WAGE_PER_WORKER = 5
GROWTH_RATE = 0.05
DEFAULT_TAX_RATE = 0.1
DEFAULT_STORAGE_CAPACITY = 100
GRID_SIZE = 10


class SimulationSystem:
    def __init__(self):
        self.state = {
            "money": 1000,
            "population": 10,
            "satisfaction": 0,
            "tax_rate": DEFAULT_TAX_RATE,
            "buildings": [],
            "residents": [],
            "resources": {"grain": 20, "wood": 20, "goods": 0},
            "storage_capacity": DEFAULT_STORAGE_CAPACITY,
            "grid": [[GRASS for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)],
            "employed": 0,
            "unemployed": 0,
            "tick": 0,
        }
        self.state["residents"] = [
            {"id": i, "employed": False, "job": None}
            for i in range(self.state["population"])
        ]
        self.state["unemployed"] = self.state["population"]
        self.state["satisfaction"] = self._compute_satisfaction()
        self._sync()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _sync(self):
        self.money = self.state.get("money", 0)
        self.population = self.state.get("population", 0)
        self.satisfaction = self.state.get("satisfaction", 0)
        self.buildings = self.state.get("buildings", [])
        self.resources = self.state.get("resources", {})

    def _buildings(self):
        return self.state.setdefault("buildings", [])

    def _population(self):
        return self.state.get("population", len(self.state.get("residents", [])))

    def _spec(self, building):
        return BUILDING_TYPES.get(building.get("type"), {})

    def _total_jobs(self):
        return sum(
            self._spec(b).get("jobs", 0) * b.get("level", 1)
            for b in self._buildings()
        )

    def _housing_capacity(self):
        return sum(
            self._spec(b).get("housing", 0) * b.get("level", 1)
            for b in self._buildings()
        )

    def _building_revenue(self):
        return sum(
            self._spec(b).get("revenue", 0) * b.get("level", 1)
            for b in self._buildings()
        )

    def _employed_count(self):
        return min(self._population(), self._total_jobs())

    def _terrain_at(self, x, y):
        grid = self.state.get("grid") or []
        try:
            cell = grid[int(y)][int(x)]
        except (IndexError, ValueError, TypeError):
            return None
        if isinstance(cell, dict):
            cell = cell.get("terrain", GRASS)
        if isinstance(cell, bool):
            return GRASS
        if isinstance(cell, int):
            return {0: GRASS, 1: WATER, 2: ROAD}.get(cell, GRASS)
        return str(cell).lower()

    def _is_buildable(self, x, y):
        terrain = self._terrain_at(x, y)
        if terrain is None or terrain in UNBUILDABLE_TERRAIN:
            return False
        for b in self._buildings():
            if b.get("x") == x and b.get("y") == y:
                return False
        return True

    def _find_free_cell(self):
        grid = self.state.get("grid") or []
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                if self._is_buildable(x, y):
                    return x, y
        return None

    def _find_building(self, ref, y=None):
        if isinstance(ref, dict):
            for b in self._buildings():
                if b is ref or b.get("id") == ref.get("id"):
                    return b
            return None
        if isinstance(ref, (tuple, list)) and len(ref) == 2:
            ref, y = ref
        if y is not None:
            for b in self._buildings():
                if b.get("x") == ref and b.get("y") == y:
                    return b
            return None
        for b in self._buildings():
            if b.get("id") == ref:
                return b
        if isinstance(ref, int) and 0 <= ref < len(self._buildings()):
            return self._buildings()[ref]
        return None

    def _compute_satisfaction(self, employed=None):
        population = self._population()
        if employed is None:
            employed = self._employed_count()
        employment_ratio = employed / population if population else 0.0
        shops = sum(1 for b in self._buildings() if b.get("type") == "shop")
        tax_rate = self.state.get("tax_rate", DEFAULT_TAX_RATE)
        capacity = self._housing_capacity()
        overcrowding = 10 if capacity and population > capacity else 0
        value = (
            50
            + 30 * employment_ratio
            + 3 * min(shops, 5)
            - 50 * tax_rate
            - overcrowding
        )
        return max(0, min(100, round(value)))

    # ------------------------------------------------------------------
    # economy
    # ------------------------------------------------------------------
    def calculate_income(self, tax_rate=None, **kwargs):
        """Total income: building revenue + resident consumption + taxes."""
        rate = self.state.get("tax_rate", DEFAULT_TAX_RATE) if tax_rate is None else tax_rate
        building_revenue = self._building_revenue()
        consumption = self._population() * CONSUMPTION_PER_CAPITA
        subtotal = building_revenue + consumption
        tax = subtotal * rate
        total = subtotal + tax
        self.state["last_income"] = {
            "building_revenue": building_revenue,
            "consumption": consumption,
            "tax": tax,
            "total": total,
        }
        return total

    def calculate_expense(self, **kwargs):
        """Total expenses: maintenance + wages + resource consumption."""
        maintenance = 0
        resource_cost = 0
        for b in self._buildings():
            spec = self._spec(b)
            level = b.get("level", 1)
            maintenance += spec.get("maintenance", 0) * level
            for res, per in spec.get("consumes", {}).items():
                resource_cost += per * level * RESOURCE_PRICES.get(res, 1)
        wages = self._employed_count() * WAGE_PER_WORKER
        total = maintenance + wages + resource_cost
        self.state["last_expense"] = {
            "maintenance": maintenance,
            "wages": wages,
            "resource_cost": resource_cost,
            "total": total,
        }
        return total

    # ------------------------------------------------------------------
    # buildings
    # ------------------------------------------------------------------
    def build_building(self, building_type=None, x=None, y=None, **kwargs):
        """Build with terrain checks, prerequisites and cost. Starts at level 1."""
        if isinstance(building_type, dict):
            spec_dict = building_type
            building_type = spec_dict.get("type") or spec_dict.get("name")
            x = spec_dict.get("x", x)
            y = spec_dict.get("y", y)
        building_type = (
            building_type
            or kwargs.get("type")
            or kwargs.get("building")
            or kwargs.get("name")
        )
        if isinstance(x, (tuple, list)) and y is None and len(x) == 2:
            x, y = x
        position = kwargs.get("position") or kwargs.get("pos")
        if position is not None and x is None:
            x, y = position
        if building_type is None:
            return False
        btype = str(building_type).lower()
        btype = BUILDING_ALIASES.get(btype, btype)
        if btype not in BUILDING_TYPES:
            return False
        spec = BUILDING_TYPES[btype]

        if x is None or y is None:
            free = self._find_free_cell()
            if free is None:
                return False
            x, y = free
        x, y = int(x), int(y)
        if not self._is_buildable(x, y):
            return False

        owned = {b.get("type") for b in self._buildings()}
        for requirement in spec.get("requires", []):
            if requirement not in owned:
                return False

        cost = spec.get("cost", 0)
        if self.state.get("money", 0) < cost:
            return False
        self.state["money"] -= cost

        building = {
            "id": len(self._buildings()),
            "type": btype,
            "x": x,
            "y": y,
            "level": 1,
        }
        self._buildings().append(building)
        self._sync()
        return building

    def upgrade_building(self, building=None, y=None, **kwargs):
        """Upgrade a building one level (up to MAX_LEVEL) for a cost."""
        target = self._find_building(building, y)
        if target is None:
            return False
        spec = self._spec(target)
        level = target.get("level", 1)
        if level >= MAX_LEVEL:
            return False
        cost = int(spec.get("cost", 0) * 0.5 * level)
        if self.state.get("money", 0) < cost:
            return False
        self.state["money"] -= cost
        target["level"] = level + 1
        self._sync()
        return target

    # ------------------------------------------------------------------
    # residents
    # ------------------------------------------------------------------
    def update_residents(self, **kwargs):
        """Assign jobs, compute satisfaction and grow the population."""
        population = self._population()
        residents = self.state.setdefault("residents", [])
        while len(residents) < population:
            residents.append(
                {"id": len(residents), "employed": False, "job": None}
            )

        job_slots = []
        for b in self._buildings():
            spec = self._spec(b)
            job_slots.extend([b.get("type")] * (spec.get("jobs", 0) * b.get("level", 1)))
        employed = min(population, len(job_slots))
        for i, resident in enumerate(residents):
            if i < employed:
                resident["employed"] = True
                resident["job"] = job_slots[i]
            else:
                resident["employed"] = False
                resident["job"] = None

        satisfaction = self._compute_satisfaction(employed=employed)

        growth = 0
        if satisfaction >= 30:
            growth = max(1, int(population * GROWTH_RATE))
        capacity = self._housing_capacity()
        new_population = population + growth
        if capacity > population:
            new_population = min(new_population, capacity)
        while len(residents) < new_population:
            residents.append(
                {"id": len(residents), "employed": False, "job": None}
            )

        self.state["population"] = new_population
        self.state["satisfaction"] = satisfaction
        self.state["employed"] = employed
        self.state["unemployed"] = new_population - employed
        self.state["tick"] = self.state.get("tick", 0) + 1
        self._sync()
        return {
            "population": new_population,
            "satisfaction": satisfaction,
            "employed": employed,
            "unemployed": new_population - employed,
            "growth": new_population - population,
        }

    # ------------------------------------------------------------------
    # resources
    # ------------------------------------------------------------------
    def manage_resources(self, action=None, resource=None, amount=None, **kwargs):
        """Run production chains and storage caps, or perform a trade."""
        if action or kwargs.get("action"):
            return self.trade(
                action or kwargs.get("action"),
                resource if resource is not None else kwargs.get("resource"),
                amount if amount is not None else kwargs.get("amount"),
                **{k: v for k, v in kwargs.items()
                   if k not in ("action", "resource", "amount")},
            )

        resources = self.state.setdefault("resources", {})
        capacity = self.state.get("storage_capacity", DEFAULT_STORAGE_CAPACITY)
        produced = {}
        consumed = {}

        for b in self._buildings():
            spec = self._spec(b)
            level = b.get("level", 1)
            scale = level
            for res, per in spec.get("consumes", {}).items():
                if per > 0:
                    scale = min(scale, resources.get(res, 0) // per)
            if scale <= 0:
                continue
            for res, per in spec.get("consumes", {}).items():
                used = per * scale
                resources[res] = resources.get(res, 0) - used
                consumed[res] = consumed.get(res, 0) + used
            for res, per in spec.get("produces", {}).items():
                made = per * scale
                resources[res] = resources.get(res, 0) + made
                produced[res] = produced.get(res, 0) + made

        for res in list(resources):
            if resources[res] > capacity:
                resources[res] = capacity
            elif resources[res] < 0:
                resources[res] = 0

        self._sync()
        return {
            "resources": dict(resources),
            "produced": produced,
            "consumed": consumed,
            "storage_capacity": capacity,
        }

    def trade(self, action, resource=None, amount=None, **kwargs):
        """Buy or sell resources for money at fixed prices."""
        resource = resource if resource is not None else kwargs.get("resource", kwargs.get("item"))
        if amount is None:
            amount = kwargs.get("amount", kwargs.get("quantity", 1))
        action = str(action).lower()
        resources = self.state.setdefault("resources", {})
        capacity = self.state.get("storage_capacity", DEFAULT_STORAGE_CAPACITY)
        if resource not in RESOURCE_PRICES:
            return False
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            return False
        if amount <= 0:
            return False
        price = RESOURCE_PRICES[resource]

        if action in ("buy", "purchase"):
            cost = price * amount
            if self.state.get("money", 0) < cost:
                return False
            if resources.get(resource, 0) + amount > capacity:
                return False
            self.state["money"] -= cost
            resources[resource] = resources.get(resource, 0) + amount
            self._sync()
            return True
        if action == "sell":
            if resources.get(resource, 0) < amount:
                return False
            resources[resource] -= amount
            self.state["money"] = self.state.get("money", 0) + price * amount
            self._sync()
            return True
        return False
