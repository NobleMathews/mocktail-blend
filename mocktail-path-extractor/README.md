# <div align="center">**Mocktail ++**</div>

## **Contents**
  * [Introduction](#introduction)
  * [Installing Dependencies](#installing-dependencies)
  * [Extracting paths from a set of projects](#extracting-paths-from-a-set-of-projects)
  * [Similar tools that inspired our implementation](#similar-tools-that-inspired-our-implementation)
  * [Team](#team)



## **Introduction**
* The idea of extracting paths from code to capture properties is inspired by [A general path-based representation for predicting program properties](https://doi.org/10.1145/3296979.3192412). We have extended the path-based representation to include CFG and PDG paths.

* This tool is based on base tool developed as part of [Kartik](https://github.com/karthikswarna) and [Dheeraj's](https://github.com/dheerajrox) bachelor thesis.



## **Installing Dependencies**
**STEP-0:** Recommended OS is Linux. Joern is not tested on Windows but still seems to work fine.


**STEP-1:** Install [Joern](https://github.com/joernio/joern)

* This library is used to extract AST, CFG, and PDG from C code snippets.

* Follow the instructions given on Joern's GitHub page to install it.

* Please make sure that the Joern scripts have the necessary execute permissions before running the tool.


**STEP-2:** Install [terashuf](https://github.com/alexandres/terashuf)

* This is used to shuffle large dataset files.

* Follow the instructions given on terashuf's GitHub page to download and compile it. 

* Build and add terashuf to path or add to bin
```
sudo mv terashuf /usr/local/bin/
```

* Please ensure both joern and terashuf can be invoked from the terminal


**STEP-3:** Install required python libraries
```
pip3 install requirements.txt
```


## **Extracting paths from a set of projects**
The script take the input parameters from the ```config.ini``` file. The parameters are explained below.

**STEP-1:** Set parameters as structured in ```config.ini```:

| Configuration Parameter | Default Value | Description                                                                                                                                                                                                             |
|-------------------------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| maxPathContexts         | -             | Maximum number of each type of path context to be extracted from a method.                                                                                                                                              |
| maxLength               | 8             | Maximum length of paths to be extracted from a method. This parameter applies only to AST paths.                                                                                                                        |
| maxWidth                | 2             | Maximum width of paths to be extracted from a method. This parameter applies only to AST paths.                                                                                                                         |
| maxTreeSize             | 200           | Maximum number of AST nodes allowed. If a method has more nodes, it will not be included in the dataset.                                                                                                                |
| separator               | \             | Special character used to separate subwords in the method names (labels) and context words.                                                                                                                             | 
| splitToken              | False         | This flag specifies whether to split the context words into subwords.                                                                                                                                                   |
| maxFileSize             | -             | Maximum filesize of the method. If a file has more size, it will not be included in the dataset.                                                                                                                        |
| upSymbol                | ↑             | Special character used to indicate the upward movement in the path.                                                                                                                                                     |
| downSymbol              | ↓             | Special character used to indicate the downward movement in the path.                                                                                                                                                   |
| labelPlaceholder        | \<SELF\>      | Special token used to replace the method name in paths and context words.                                                                                                                                               |
| useParentheses          | True          | This flag specifies whether to place path's nodes inside parenthesis.                                                                                                                                                   |
| useCheckpoint           | -             | This flag specifies whether to use the existing dataset file and resume the path extraction process. If this is true, make sure that all the parameters are unchanged from the previous run.                            |
| notIncludeMethods       | -             | Comma-separated list of method names that should not be included in the dataset. For example, some method names like 'f' may not represent the method's meaning, and hence we can remove such methods from the dataset. |
| maxASTPaths             | 0             | Maximum number of AST paths to be included from each method in the dataset.                                                                                                                                             |
| maxCFGPaths             | 0             | Maximum number of CFG paths to be included from each method in the dataset.                                                                                                                                             |
| maxCDGPaths             | 0             | Maximum number of CDG paths to be included from each method in the dataset.                                                                                                                                             |
| maxDDGPaths             | 0             | Maximum number of DDG paths to be included from each method in the dataset.                                                                                                                                             |
| train_split             | -             | Percentage of paths in training set                                                                                                                                                                                     |
| test_split              | -             | Percentage of paths in testing set                                                                                                                                                                                      |
| val_split               | -             | Percentage of paths in validation set                                                                                                                                                                                   |
| generateAll             | -             | If this field is set to true all representations (ast, cfg, pdg & ddg) will be generated                                                                                                                                |

**STEP-2:** Add dataset to be processed into ```1_input``` and update config file based on task to be performed

- 1_input expects a set of project dirs
- 2_processed content:
  - if "method" option is selected for each project directory, extract all C functions and save in corresponding project folder 
  - if "file" option is selected the files are filtered directly

- If outputType is 'method':

  - For each project directory, all C functions are extracted and saved in the corresponding project directory in outPath.
  - This option generates output such that it can be used for method naming

- If outputType is 'file':
    
  - This option generated output for processing at a file level rather than at method level

* The maxFileSize parameter can be used to limit the size of the functions extracted from the projects.

* Run the script to extract the methods and format output required to train the extended model.
```
cd mocktail-path-extractor
python3 pipeline.py
```

* Choose additional options as required among the cli options presented

* Run the ```output_formatter.py``` script to convert the dataset file into code2vec's format.
```
python3 output_formatter.py
```

## **Similar tools that inspired our implementation**
1. [astminer](https://github.com/JetBrains-Research/astminer)
2. [code2vec's Java extractor](https://github.com/tech-srl/code2vec/tree/master/JavaExtractor)



## **Team**
In case of any queries or if you would like to give any suggestions, please feel free to contact:

- Karthik Chandra (cs17b026@iittp.ac.in) 

- Noble Saji Mathews (ch19b023@iittp.ac.in)

- Dheeraj Vagavolu (cs17b028@iittp.ac.in) 

- Sridhar Chimalakonda (ch@iittp.ac.in)