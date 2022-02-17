set terminal postscript enhanced color "Times-Roman" 20
set xlabel ""
set ylabel "E - E_F (eV)"
set nokey
set title "alpha Si"
set arrow from  0.00000, -9.0 to  0.00000,  5.0 nohead
set arrow from  0.21495, -9.0 to  0.21495,  5.0 nohead
set arrow from  0.85980, -9.0 to  0.85980,  5.0 nohead
set arrow from  1.38631, -9.0 to  1.38631,  5.0 nohead
set arrow from  1.81621, -9.0 to  1.81621,  5.0 nohead
set arrow from  2.12020, -9.0 to  2.12020,  5.0 nohead
set arrow from  2.72817, -9.0 to  2.72817,  5.0 nohead
set arrow from  0.00000, 0.0 to  2.72817, 0.0 nohead lt 3
set xtics ("X"  0.00000, \
           "K"  0.21495, \
           " "  0.85980, \
           "L"  1.38631, \
           "W"  1.81621, \
           "X"  2.12020, \
           " "  2.72817  )
set label "G" at   0.85980, -9.65 center font "Symbol,20"
set label "G" at   2.72817, -9.65 center font "Symbol,20"
set ytics -8,2,4
plot [0:  2.72818] [-9:5] \
"bands.1" using 1:($2+0.00)  w p pt  7 ps 0.5
