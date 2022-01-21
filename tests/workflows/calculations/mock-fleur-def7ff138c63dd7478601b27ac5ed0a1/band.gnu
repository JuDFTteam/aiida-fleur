set terminal postscript enhanced color "Times-Roman" 20
set xlabel ""
set ylabel "E - E_F (eV)"
set nokey
set title "alpha Si"
set arrow from  0.00000, -9.0 to  0.00000,  5.0 nohead
set arrow from  0.48064, -9.0 to  0.48064,  5.0 nohead
set arrow from  1.12549, -9.0 to  1.12549,  5.0 nohead
set arrow from  1.65201, -9.0 to  1.65201,  5.0 nohead
set arrow from  2.08191, -9.0 to  2.08191,  5.0 nohead
set arrow from  2.08191, -9.0 to  2.08191,  5.0 nohead
set arrow from  2.38589, -9.0 to  2.38589,  5.0 nohead
set arrow from  2.99386, -9.0 to  2.99386,  5.0 nohead
set arrow from  0.00000, 0.0 to  2.99386, 0.0 nohead lt 3
set xtics ("X"  0.00000, \
           "K"  0.48064, \
           "G"  1.12549, \
           "L"  1.65201, \
           "W"  2.08191, \
           "W"  2.08191, \
           "X"  2.38589, \
           "G"  2.99386  )
set ytics -8,2,4
plot [0:  2.99387] [-9:5] \
"bands.1" using 1:($2+0.00)  w p pt  7 ps 0.5
