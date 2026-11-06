"""Deterministic synthetic dataset dimensions and presets."""
from dataclasses import dataclass
SEED=20261022
@dataclass(frozen=True)
class DatasetConfig:
    name:str
    orders:int
    skus:int
    nodes:int
    carriers:int
    tracking_events:int
    def __post_init__(self):
        if min(self.orders,self.skus,self.nodes,self.carriers,self.tracking_events)<=0:
            raise ValueError("Dataset dimensions must be positive")
STARTER=DatasetConfig("starter",100,50,5,3,500)
FULL=DatasetConfig("full",50000,500,20,10,100000)
