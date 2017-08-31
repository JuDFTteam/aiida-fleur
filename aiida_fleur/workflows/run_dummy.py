#%load_ext autoreload
#%autoreload 2
#%matplotlib notebook

from aiida import load_dbenv, is_dbenv_loaded
if not is_dbenv_loaded():
    load_dbenv()

# import dummy_wc from where ever it is
from aiida_fleur.workflows.dummy import dummy_wc
from pprint import pprint
from aiida.orm.data.base import Str
from aiida.work.run import submit, async

input_s = Str('hello world!')


res = dummy_wc.run(str_display=input_s)

# if you check the output nodes of the submit run, there will be none
res1 = submit(dummy_wc, str_display=input_s)

#res2 = async(dummy_wc, str_display=input_s)
