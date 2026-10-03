"""
pairwise-simulation-system - SimulationSystem

This module contains a deliberately broken implementation.
Fix all bugs so that tests pass.
"""


class SimulationSystem:
    def __init__(self):
        self.state = {}

    def calculate_income(self, *args, **kwargs):
        """BUG: 收入计算不做建筑加成，建了商店也不增加收入"""
        return None

    def calculate_expense(self, *args, **kwargs):
        """BUG: 支出不做维护费，建筑建完不花钱维护"""
        return None

    def build_building(self, *args, **kwargs):
        """BUG: 建筑不做位置检查，能建在水上和路上"""
        return None

    def update_residents(self, *args, **kwargs):
        """BUG: 居民不做满意度，永远是0"""
        return None

    def manage_resources(self, *args, **kwargs):
        """BUG: 资源不做存储上限，无限存储"""
        return None

