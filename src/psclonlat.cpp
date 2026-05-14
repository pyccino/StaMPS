// *********************************************************************
// psclonlat: Extract lon/lat for PS Candidates
// ---------------------------------------------------------------------
// AUTHOR    : Andy Hooper
// ---------------------------------------------------------------------
// WRITTEN   : 10.03.2005
//
// Change History
// ==============================================
// 03/2009 MA Fix for gcc 4.3.x
// ==============================================

#include <iostream>
using namespace std;

#include <fstream>
using namespace std;

#include <complex>
using namespace std;

#include <string>
using namespace std;

#include <cmath>
using namespace std;

#include <cstdio>
using namespace std;

#include <cstdlib>
using namespace std;

#include <cstdint>

#include "stamps_locale.h"

// =======================================================================
// Start of program
// =======================================================================

//int main(long  argc, char *argv[] ) {
int main(int  argc, char *argv[] ) {    // [MA]  long --> int for gcc 4.3.x
  STAMPS_PIN_C_LOCALE();

try {

  if (argc < 2)
  {
     cout << "Usage: psclonlat parmfile pscands.1.ij pscands.1.ll" << endl << endl;
     cout << "Input parameters:" << endl;
     cout << "  parmfile   (input)  width of lon/lat files (range bins)" << endl;
     cout << "                      name of lon file (float)" << endl;
     cout << "                      name of lat file (float)" << endl;
     cout << "  pscands.1.ij (input)  location of permanent scatterer candidiates" << endl;
     cout << "  pscands.1.ll (output) lon/lat of permanent scatterer candidiates" << endl << endl;
     throw "";
  }

//  char *ijname;
  const char *ijname;          // [MA] deprication fix
  if (argc < 3)
     ijname="pscands.1.ij";
  else ijname = argv[2];

//  char *outfilename;
  const char *outfilename;     // [MA] deprication fix
  if (argc < 4)
     outfilename="pscands.1.ll";
  else outfilename = argv[3];


  ifstream parmfile (argv[1], ios::in);
  parmfile.imbue(std::locale::classic());
  if (! parmfile.is_open())
  {
      cout << "Error opening file " << argv[1] << endl;
      throw "";
  }

  ifstream psfile (ijname, ios::in|ios::binary);
  psfile.imbue(std::locale::classic());
  cout << "opening " << ijname << "...\n";

  if (! psfile.is_open())
  {
      cout << "Error opening file " << ijname << endl;
      throw "";
  }

  // [Windows fix] ios::binary required: outfile holds raw floats
  // (lon/lat pairs). Text mode on Windows translates 0x0A bytes to
  // 0x0D 0x0A, corrupting the binary stream and inflating the file
  // size. MATLAB-side ps_load_initial_gamma then reads (filesize/8)
  // lon/lat pairs which no longer match n_ps from pscands.1.ij,
  // failing at ps_load_initial_gamma:191 (xy concatenation).
  ofstream outfile(outfilename,ios::out|ios::binary);
  outfile.imbue(std::locale::classic());
  if (! outfile.is_open())
  {
      cout << "Error opening file " << outfilename << endl;
      throw "";
  }

  char line[256];
  int num_files = 2;
  int width = 0;
  char ifgfilename[256];

  parmfile >> width;
  cout << "width = " << width << "\n";
  parmfile.getline(ifgfilename,256);

  ifstream* ifgfile   = new ifstream[num_files];
  float* calib_factor = new float[num_files];

  for (int i=0; i<num_files; ++i)
  {
    parmfile >> ifgfilename;
    ifgfile[i].open (ifgfilename, ios::in|ios::binary);
    ifgfile[i].imbue(std::locale::classic());
    cout << "opening " << ifgfilename << "...\n";

    if (! ifgfile[i].is_open())
    {
        cout << "Error opening file " << ifgfilename << endl;
	throw "";
    }

    char header[32];
    int32_t magic=0x59a66a95;
    ifgfile[i].read(header,32);
    if (*reinterpret_cast<int32_t*>(header) == magic)
        cout << "sun raster file - skipping header\n";
    else ifgfile[i].seekg(ios::beg);

  }

  parmfile.close();

  char buffer[1000];
  char ifg_pixel[sizeof(float)];;
  int pscid=0;
  int x=0;
  int y=0;

  psfile >> pscid >> y >> x;
  psfile.getline(buffer,1000);

  std::streamoff xyaddr_save = 0;

  while (! psfile.eof() )
  //for (int dummyi=0; dummyi<100; dummyi++)
  {
    // Promote to streamoff before the multiplication so the offset is
    // computed in 64-bit arithmetic on LLP64 targets (Win64), where
    // int*int overflows for large rasters and `long` is only 32 bits.
    std::streamoff xyaddr = (static_cast<std::streamoff>(y)*width+x)*sizeof(float);

    for ( int i=0; i<num_files; i++)
    {
      ifgfile[i].seekg(xyaddr, ios::beg);
      ifgfile[i].read (ifg_pixel, sizeof(float));
      outfile.write(ifg_pixel, sizeof(float));
    }

    if (pscid/100000.0 == rint(pscid/100000.0))
      cout << pscid << " PS candidates processed\n";

    psfile >> pscid >> y >> x;
    psfile.getline(buffer,1000);
  }


  }
  catch( char * str ) {
     cout << str << "\n";
     return 1;
  }
  catch( ... ) {
    return 1;
  }

  return(0);

};
