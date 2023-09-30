int main(int argc, char **argv) {

  int x = 0, y = 2;
  int z;

  if (x == y) {
    if(x == 2) {
      z = 1;
    } else {
      z = 2;
    }
  } else {
    if(x == 3) {
      z = 3;
    } else {
      z = 4;
    } if (x == 4)  {
      z = 5;
    }
  }
  z = x + 1;
  while(x != 5) {
    x += x;
  }

  for(int i = 0; i < x; i++) {
    x -= 2;
  }

  return x;
}