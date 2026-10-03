"""pairwise-simulation-system - SimulationSystem

A small city-building simulation with balanced economy, buildings,
residents and resources.
"""

TERRAIN_LAND = "land"
TERRAIN_WATER = "water"
TERRAIN_ROAD = "road"

BUILDING_TYPES = {
    "house": {
        "cost": 100,
        "maintenance": 5,
        "income": 0,
        "jobs": 0,
        "residents": 4,
        "requires": [],
    },
    "shop": {
        "cost": 200,
        "maintenance": 10,
        "income": 40,
        "jobs": 4,
        "residents": 0,
        "requires": ["house"],
    },
    "factory": {
        "cost": 500,
        "maintenance": 25,
        "income": 100,
        "jobs": 10,
        "residents": 0,
        "requires": ["house", "shop"],
    },
}

MAX_LEVEL = 3
LEVEL_MULTIPLIER = {1: 1.0, 2: 1.5, 3: 2.0}

# Production chain: raw materials are refined into finished goods.
PRODUCTION_CHAIN = {"raw": "goods"}
RAW_PER_GOOD = 2

RESOURCE_PRICES = {"raw": 5, "goods": 15}


class SimulationSystem:
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height
        self.grid = [[TERRAIN_LAND for _ in range(width)] for _ in range(height)]
        self.money = 1000
        self.tax_rate = 0.1
        self.population = 10
        self.satisfaction = 50
        self.buildings = []
        self.storage_capacity = 100
        self.resources = {"raw": 20, "goods": 0}
        self.state = {}

    # ------------------------------------------------------------------
    # Economy
    # ------------------------------------------------------------------
    def calculate_income(self, *args, **kwargs):
        """Income = building bonuses + resident consumption + taxes."""
        building_income = sum(
            BUILDING_TYPES[b["type"]]["income"] * LEVEL_MULTIPLIER[b["level"]]
            for b in self.buildings
        )
        consumption = self.population * 2
        taxes = self.population * 10 * self.tax_rate
        total = building_income + consumption + taxes
        self.state["income"] = {
            "buildings": building_income,
            "consumption": consumption,
            "taxes": taxes,
            "total": total,
        }
        return total

    def calculate_expense(self, *args, **kwargs):
        """Expense = building maintenance + wages + resource consumption."""
        maintenance = sum(
            BUILDING_TYPES[b["type"]]["maintenance"]
            * LEVEL_MULTIPLIER[b["level"]]
            for b in self.buildings
        )
        employed = self._assigned_jobs()
        wages = employed * 3
        resource_cost = self._production_raw_cost() * RESOURCE_PRICES["raw"]
        total = maintenance + wages + resource_cost
        self.state["expense"] = {
            "maintenance": maintenance,
            "wages": wages,
            "resources": resource_cost,
            "total": total,
        }
        return total

    # ------------------------------------------------------------------
    # Buildings
    # ------------------------------------------------------------------
    def build_building(self, building_type="house", x=0, y=0, *args, **kwargs):
        """Build with position checks, prerequisites and level tracking."""
        if building_type not in BUILDING_TYPES:
            return None
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        if self.grid[y][x] != TERRAIN_LAND:
            return None
        if any(b["x"] == x and b["y"] == y for b in self.buildings):
            return None
        spec = BUILDING_TYPES[building_type]
        owned = {b["type"] for b in self.buildings}
        if any(req not in owned for req in spec["requires"]):
            return None
        if self.money < spec["cost"]:
            return None
        self.money -= spec["cost"]
        building = {"type": building_type, "x": x, "y": y, "level": 1}
        self.buildings.append(building)
        return building

    def upgrade_building(self, building):
        """Upgrade a building one level (up to MAX_LEVEL)."""
        if building not in self.buildings:
            return None
        if building["level"] >= MAX_LEVEL:
            return None
        cost = BUILDING_TYPES[building["type"]]["cost"] // 2
        if self.money < cost:
            return None
        self.money -= cost
        building["level"] += 1
        return building

    # ------------------------------------------------------------------
    # Residents
    # ------------------------------------------------------------------
    def update_residents(self, *args, **kwargs):
        """Update satisfaction, population growth and job assignment."""
        jobs = sum(
            BUILDING_TYPES[b["type"]]["jobs"] * b["level"] for b in self.buildings
        )
        employed = min(self.population, jobs)
        employment_ratio = employed / self.population if self.population else 0
        capacity = sum(
            BUILDING_TYPES[b["type"]]["residents"] * b["level"]
            for b in self.buildings
        )
        housing_ratio = (
            min(1.0, capacity / self.population) if self.population else 1.0
        )

        self.satisfaction = max(
            0,
            min(
                100,
                int(
                    50
                    + 40 * employment_ratio
                    + 20 * housing_ratio
                    - 100 * self.tax_rate
                ),
            ),
        )

        if self.satisfaction >= 60:
            growth = max(1, self.population // 10)
        elif self.satisfaction <= 20:
            growth = -max(1, self.population // 20)
        else:
            growth = 0
        self.population = max(0, self.population + growth)

        self.state["residents"] = {
            "population": self.population,
            "satisfaction": self.satisfaction,
            "employed": min(self.population, jobs),
            "unemployed": max(0, self.population - jobs),
        }
        return self.state["residents"]

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    def manage_resources(self, *args, **kwargs):
        """Enforce storage caps, run the production chain and trading."""
        factories = [b for b in self.buildings if b["type"] == "factory"]
        produced = 0
        for factory in factories:
            goods = factory["level"]
            if self.resources["raw"] >= goods * RAW_PER_GOOD:
                self.resources["raw"] -= goods * RAW_PER_GOOD
                self.resources["goods"] += goods
                produced += goods

        for name, amount in self.resources.items():
            if amount > self.storage_capacity:
                self.resources[name] = self.storage_capacity

        self.state["resources"] = dict(self.resources)
        self.state["produced"] = produced
        return self.state["resources"]

    def trade_resource(self, name, amount):
        """Buy (positive amount) or sell (negative amount) a resource."""
        if name not in RESOURCE_PRICES or amount == 0:
            return None
        price = RESOURCE_PRICES[name]
        if amount > 0:
            cost = amount * price
            if self.money < cost:
                return None
            if self.resources[name] + amount > self.storage_capacity:
                return None
            self.money -= cost
            self.resources[name] += amount
        else:
            if self.resources[name] < -amount:
                return None
            self.money += -amount * price
            self.resources[name] += amount
        return self.resources[name]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _assigned_jobs(self):
        jobs = sum(
            BUILDING_TYPES[b["type"]]["jobs"] * b["level"] for b in self.buildings
        )
        return min(self.population, jobs)

    def _production_raw_cost(self):
        factories = [b for b in self.buildings if b["type"] == "factory"]
        consumed = 0
        remaining = self.resources["raw"]
        for factory in factories:
            need = factory["level"] * RAW_PER_GOOD
            if remaining >= need:
                remaining -= need
                consumed += need
        return consumed
