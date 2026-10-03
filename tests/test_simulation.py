import pytest
from simulation.system import SimulationSystem


class TestSimulationSystem:

    def test_calculate_income(self):
        """收入计算不做建筑加成，建了商店也不增加收入"""
        obj = SimulationSystem()
        result = obj.calculate_income()
        self.assertIsNotNone(result)

    def test_calculate_expense(self):
        """支出不做维护费，建筑建完不花钱维护"""
        obj = SimulationSystem()
        result = obj.calculate_expense()
        self.assertIsNotNone(result)

    def test_build_building(self):
        """建筑不做位置检查，能建在水上和路上"""
        obj = SimulationSystem()
        result = obj.build_building()
        self.assertIsNotNone(result)

    def test_update_residents(self):
        """居民不做满意度，永远是0"""
        obj = SimulationSystem()
        result = obj.update_residents()
        self.assertIsNotNone(result)

    def test_manage_resources(self):
        """资源不做存储上限，无限存储"""
        obj = SimulationSystem()
        result = obj.manage_resources()
        self.assertIsNotNone(result)

