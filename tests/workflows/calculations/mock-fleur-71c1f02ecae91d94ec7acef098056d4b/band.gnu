set terminal postscript enhanced color "Times-Roman" 20
set xlabel ""
set ylabel "E - E_F (eV)"
set nokey
set title "alpha Si"
set arrow from  0.00000, -9.0 to  0.00000,  5.0 nohead
set arrow from  0.60797, -9.0 to  0.60797,  5.0 nohead
set arrow from  0.82292, -9.0 to  0.82292,  5.0 nohead
set arrow from  1.19522, -9.0 to  1.19522,  5.0 nohead
set arrow from  1.84007, -9.0 to  1.84007,  5.0 nohead
set arrow from  2.36659, -9.0 to  2.36659,  5.0 nohead
set arrow from  2.79649, -9.0 to  2.79649,  5.0 nohead
set arrow from  3.10047, -9.0 to  3.10047,  5.0 nohead
set arrow from  0.00000, 0.0 to  3.10047, 0.0 nohead lt 3
set xtics ("G"  0.00000, \
           "X"  0.60797, \
           "U"  0.82292, \
           "K"  1.19522, \
           "G"  1.84007, \
           "L"  2.36659, \
           "W"  2.79649, \
           "X"  3.10047  )
set ytics -8,2,4
plot [0:  3.10048] [-9:5] \
"bands.1" using 1:($2+0.00)  w p pt  7 ps 0.5
