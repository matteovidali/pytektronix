from pytektronix.pytektronix_base_classes import Scope

class TestScope(Scope):
   def __init__(self):
      self.strings = {}
      pass

   def ask(self, q: str) -> str:
      if q.endswith("?"):
         q = q.replace("?", "")
      if q not in self.strings.keys():
         self.strings[q] = "1"
        
      return self.strings[q]

   def write(self, q: str) -> None:
      setting, value = q.split(" ")
      if not value:
         raise ValueError("NO VALUE")
      self.strings[setting] = value

if __name__ == "__main__":
   pass
