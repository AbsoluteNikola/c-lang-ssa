int main() {
  int x = 2;
  while(x < 5) {
    x += x;
  }
  return x;
//  return (x == 2) ? (x + 6) : (x - 3) ;
}


int foo(int x) {
  while(x < 10) {
    x++;
  }
  return x;
}