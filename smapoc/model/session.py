import ast

class Session:
    def __init__(self):
        self.laser_sn= ""

    def set_laser_sn(self, sn: str) -> None:
        self.laser_sn = sn

    def get_laser_sn(self) -> str:
        return self.laser_sn



    def set_force_profile(self, profile: str) -> None:
        self.force_profile = ast.literal_eval(profile)

    def get_force_profile(self) -> str:
        return self.force_profile