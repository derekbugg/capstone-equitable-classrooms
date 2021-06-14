from numpy.core.numeric import isclose
import pandas as pd
from pandas import ExcelWriter
import numpy as np
import math
import random
from pandas.core.arrays.integer import Int32Dtype
from pandas.core.indexes.api import get_objs_combined_axis

SCHOOL_FILE= 'Grade Level_20210509_Names_Removed.xls'

# The file provided by the school indicates students' previous grade level.
EXIT_GRADES= ['KG', '01', '02', '03', '04', '05']

# These are the "yes/no or male/female" categories
BINARY_CATEGORIES=['504 - 2020-2021','Gender','LAP Indicator - 2020-2021']

# Special Education and gifted student require clustering.
CLUSTERED_CATEGORIES =['SPED','HCP - 2020-2021']

# This category group is based on numerical standardized test scores.
NOMINAL_CATEGORIES = ['IRLA-Score - 2020-2021', 'iReady-ELA Score Winter - 2020-2021', 'iReady-Math Score Winter - 2020-2021',]

# Attendance metric divides into 3 groups per client requirements.
ATTENDANCE_CATEGORY = ['Attn % - 2020-2021']

# Race is a special category because affinity clusters' and balance across classrooms will be solved.
SPECIAL_CATEGORY = ['Race']

#These are the only races defined by School Information System Database.
RACES = ['Asian', 'Black', 'Hispanic', 'Native', 'Multiple', 'Pacific Islander', 'White'] 

ALL_CATEGORIES = [BINARY_CATEGORIES + CLUSTERED_CATEGORIES + NOMINAL_CATEGORIES + ATTENDANCE_CATEGORY + RACES]

# This file defines acceptable clusters for special education based on staffing resources. 
CLUSTER_FILE = 'SPED_Clusters.xlsx'

# This file defines acceptable clusters for race affinity groups. 
CLUSTER_FILE_FLOAT = 'Race_Affinity_Clusters.xlsx'

# Tolerances set by end user, but established in this instance by collaborating school administrator (client).  Increasing these values increases runtime, but increases balance. 
GENDER_TOL = .20
IEP_TOL = 1
LAP_TOL = .25
ATTENDANCE_TOL = .3
IRLA_TOL = .25


def convert_attribs(student_body):
    """Clean white space from student body file.  Convert 'yes/no' or 'male/female' categories to 1's and 0's.  Convert attendance category from string type % to float type %."""

    # Trim all whitespace from dataframe.
    student_body.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Change 'yes/no' categories to '1' or '0'.
    student_body['SPED'] = np.where(student_body['SPED'] == 'Yes', 1, 0)
    student_body['HCP - 2020-2021'] = np.where(student_body['HCP - 2020-2021'].str.contains('Yes'), 1, 0)
    student_body['504 - 2020-2021'] = np.where(student_body['504 - 2020-2021'].str.contains('Yes'), 1, 0)
    student_body['Gender'] = np.where(student_body['Gender'].str.contains('Male'), 1, 0)
    student_body['LAP Indicator - 2020-2021'] = np.where(student_body['LAP Indicator - 2020-2021'].str.contains('Yes'), 1, 0)
    
    # Convert string attendance % to float.
    student_body['Attn % - 2020-2021'] = student_body['Attn % - 2020-2021'].str.replace('%', '').astype(float)
    
    student_body = categorize_attendance(student_body)

    return student_body

def classes_per_grade(grade, num):
    """Ask administrator how many classes should be formed based
    on the number of students."""

    # Transition students to the following year's grade.  File provided as input to this program indicates students' previous year's grade level
    grade +=1

    # Ask for input from user based on staff resources available next year.
    print(f"There are {num} students coming into grade {grade} next year.")
    classes = float(input("\nHow many classes for this grade would you like to form?"))

    return classes

        
    
def num_per_grade(all_grades):
    """Count the number of students in each grade and return a list containing the number of students per exiting grade. Index 0= Kindergarten, 1= First Grade, etc."""
    
    sizes = []
    for students in all_grades:
        students_per_grade = (len(students.index))
        sizes.append(students_per_grade)
    
    return sizes

    
def initialize_data():
    """Import student data from file and create a dataframe, call function to convert string data to ints and floats, and group students by grade. """
    
    
    # Import student data from school district program output. 
    all_students = pd.read_excel(SCHOOL_FILE, index_col = [1], header=[10])

    # Convert string categories to integers and floats.
    conv_students = convert_attribs(all_students)

    # Group students by grade.
    gradegroups = conv_students.groupby(conv_students.Grade)
    kg = gradegroups.get_group('KG')
    firstg = gradegroups.get_group('01')
    secondg = gradegroups.get_group('02')
    thirdg = gradegroups.get_group('03')
    fourthg = gradegroups.get_group('04')
    fifthg = gradegroups.get_group('05')

    students_by_grade = [kg, firstg, secondg, thirdg, fourthg, fifthg]

    return students_by_grade
    
def how_many_classes(st_by_grade):    
    """Determine how many classes will be formed and return a list which indicates number of students per grade."""

    # Find the amount of students in each grade
    grade_sizes = num_per_grade(st_by_grade)

    # Ask school administrator how many classes per grade based on staffing
    num_classes = []
    
    for this_grade in range(len(grade_sizes)):
        classes = classes_per_grade(this_grade, grade_sizes[this_grade])
        num_classes.append(classes)

    return num_classes


def shuffle(grades_to_shuffle):
    """Shuffle students randomly and return a list of dataframes of students grouped by grade.""" 

    shuffled = []
    for grades in grades_to_shuffle:
        random = grades.sample(frac=1)
        shuffled.append(random)
    return shuffled

def divide_into_classes(grades, n_classes):
    """Split all students in the same grade by the number of classes which was provided by the school administrator.""" 
    
    next_grades = []
    i = 0
    for x in grades:
        num = n_classes[i]
        nextgrade = np.array_split(x, num)
        next_grades.append(nextgrade)
        i+=1
    return next_grades

def missing_scores_school(all_classes_by_grade):
    """Fills missing test scores of each grade in the whole student body with the average test score of that grade and returns the whole student body file cleaned.  Only conducted once."""

    ''' TODO ask client whether or not empty scores should use the average of the other test scores or use a lower score due to the fact that it looks like those who have missing scores are underperforming in other areas as well'''

    for grade in all_classes_by_grade:
        for cls in grade:
            cls = cls.fillna(cls.mean())

    return all_classes_by_grade

def reshuffle_one_grade(grade):
    """Reshuffle one grade of students and return the grade student body."""

    num = len(grade)
    reshuffled = grade.loc[random.sample(list(grade.index),num)]

    return reshuffled

def divide_one_grade(grade, n_classes):
    """Divide one grade of students by the number of classes and return the classes of students."""

    classes= np.array_split(grade, n_classes)
    return classes

def missing_scores_gradelevel(grade):
    """Fill missing test scores of each class in one grade with the average of the one class and return the dataframe of the grade."""

    ''' TODO ask client wether or not empty scores should use the average of the other test scores, or use a lower score due to the fact that it looks like those who have missing scores are underperforming in other areas as well.'''
    
    for cls in grade:
        cls = cls.fillna(cls.mean())
    
    return grade

def categorize_attendance(all_students):
    """Convert student body attendance from % to three categories."""

    all_students.loc[all_students['Attn % - 2020-2021'] > 90, 'Attn % - 2020-2021'] = 0
    all_students.loc[all_students['Attn % - 2020-2021'] > 80, 'Attn % - 2020-2021'] = 1 
    all_students.loc[all_students['Attn % - 2020-2021'] > 3, 'Attn % - 2020-2021'] = 2
    return all_students

def calculate(classes_to_check):
    """For every class in every grade, calc averages and other data, and store them in a list of new dataframes and return the list. This only runs once."""

    gender_list = []
    iep_list = []
    lap_list = []
    sped_list = []
    hcp_list = []
    grade_list = []
    att_list = []
    irla_list = []
    asian_list = []
    black_list = []
    hispanic_list =[]
    multi_list = []
    native_list = []
    pi_list = []
    white_list = []

    racedf = pd.DataFrame(columns = RACES)

    for grade_levels in classes_to_check:
        i =0
        for c in grade_levels:
            iep_calc = c['504 - 2020-2021'].sum()/len(c)
            iep_list.append(iep_calc)
            att_calc = c['Attn % - 2020-2021'].sum()/len(c)
            att_list.append(att_calc)
            gender_calc = c['Gender'].sum()/len(c)
            gender_list.append(gender_calc)
            lap_calc = c['LAP Indicator - 2020-2021'].sum()/len(c)
            lap_list.append(lap_calc)
            sped_total = c['SPED'].sum()
            sped_list.append(sped_total)
            hcp_total = c['HCP - 2020-2021'].sum()
            hcp_list.append(hcp_total)
            irla_calc = c['IRLA-Score - 2020-2021'].sum()/len(c)
            irla_list.append(irla_calc)
            race_int= c['Race'].value_counts()
            racedf = racedf.append(race_int, ignore_index=True)
            racedf = racedf.fillna(0)
            asian_list = racedf['Asian'].values.tolist()
            black_list = racedf['Black'].to_list()
            hispanic_list = racedf['Hispanic'].to_list()
            multi_list = racedf['Multiple'].to_list()
            native_list = racedf['Native'].to_list()
            pi_list = racedf['Pacific Islander'].to_list()
            white_list = racedf['White'].to_list()                      
            g = c.iloc[0]['Grade']
            grade_list.append(g)

        i= i +1
                
        
    # Instantiate and populate a df for calculations.
    calc = pd.DataFrame(columns=ALL_CATEGORIES,index=grade_list).rename_axis('Classes')
    calc['Gender']= gender_list
    calc['504 - 2020-2021'] = iep_list
    calc['LAP Indicator - 2020-2021'] = lap_list
    calc['SPED'] = sped_list
    calc['HCP - 2020-2021'] = hcp_list
    calc['Attn % - 2020-2021'] = att_list
    calc['IRLA-Score - 2020-2021'] = irla_list
    calc['Asian'] = asian_list
    calc['Black'] = black_list
    calc['Hispanic'] = hispanic_list
    calc['Multiple'] = multi_list
    calc['Native'] = native_list
    calc['Pacific Islander'] = pi_list
    calc['White'] = white_list

    # Create new dfs for each grade's calculations.
    calc1 = calc.loc[calc.index == EXIT_GRADES[0]]
    calc2 = calc.loc[calc.index == EXIT_GRADES[1]]
    calc3 = calc.loc[calc.index == EXIT_GRADES[2]]
    calc4 = calc.loc[calc.index == EXIT_GRADES[3]]
    calc5 = calc.loc[calc.index == EXIT_GRADES[4]]
    calc6 = calc.loc[calc.index == EXIT_GRADES[5]]
    calc_dfs = [calc1, calc2, calc3, calc4, calc5, calc6]

    return calc_dfs

def check_clusters(grade_to_check):
    """Determine if the special education and gifted student of this grade fall into acceptable clusters defined by school."""

    nclasses = len(grade_to_check)   
    clusters_good = True
    sped_clus_good = True
    hicap_clus_good = True
    school_clusters = pd.read_excel(CLUSTER_FILE, header=None, sheet_name=((nclasses)-2))
    cluster_lists = school_clusters.values.tolist()

    # If there's only one class, clusters are not applicable. 
    if nclasses == 1:
        return clusters_good
        pass
    else: 
        sped = sorted(grade_to_check['SPED'].values.tolist())
        sped = [i[0] for i in sped]
        hcp = sorted(grade_to_check['HCP - 2020-2021'].values.tolist())
        hcp = [i[0] for i in hcp]
        if sped in cluster_lists:
            sped_clus_good = True
        else:
            sped_clus_good = False
        if hcp in cluster_lists:
            hicap_clus_good = True
        else:
            hicap_clus_good = False
        clusters_good = hicap_clus_good and sped_clus_good
        return clusters_good
        
def affinity_diversity_check(grade_to_check):
    """Determine if the special education and gifted student of this grade fall into acceptable clusters defined by school and return true or false."""

    nclasses = len(grade_to_check)
    check_good = True
    school_clusters = pd.read_excel(CLUSTER_FILE_FLOAT, header=None, sheet_name=((nclasses)-2), dtype=str)
    school_clusters = school_clusters.astype(float)
    cluster_lists = school_clusters.values.tolist()
    race_dict = {}

    # If there's only one class, clusters are not applicable.
    if nclasses == 1:
        check_good = True
        return check_good
        pass 
    else:
        i = 0
        for race in RACES:
            race_list = sorted(grade_to_check[race].values.tolist())
            race_list = [i[0] for i in race_list]
            race_sum = sum(race_list)
            #If there are 10 or more of one race we will not check for clusters. The rationale being that affinity at school is somewhat less important for large race groups. TODO This could lead to students without affinity (one student of a given race in a classroom with no race peers). This is not ideal no matter the student's race. Solving for a larger number of one race has led to extensive runtimes. 
            if (race_sum > 9):
                race_dict[i] = True
            else:
                if (sorted(race_list) in cluster_lists):
                    race_dict[i] = True            
                else:
                    race_dict[i] = False
            i = i +1

    check_good = all(race_dict.values())
    return check_good 

def calculate_one_grade(grade):
    """For every class in the one grade provided, calc averages and other data, and store them in a new dataframe and return the dataframe."""

    """TODO This function is almost identical to the 'calculate' function, except that this code runs when the first classrooms set by 'calculate' do not meet acceptance tolerances. Restructure code in order to be more elegant and pythonic. Ran out of time."""

    gender_list = []
    iep_list = []
    lap_list = []
    sped_list = []
    hcp_list = []
    grade_list = []
    att_list = []
    irla_list = []
    asian_list = []
    black_list = []
    hispanic_list =[]
    multi_list = []
    native_list = []
    pi_list = []
    white_list = []

    racedf = pd.DataFrame(columns = RACES)

    for c in grade:
        iep_calc = c['504 - 2020-2021'].sum()/len(c)
        iep_list.append(iep_calc)
        att_calc = c['Attn % - 2020-2021'].sum()/len(c)
        att_list.append(att_calc)
        gender_calc = c['Gender'].sum()/len(c)
        gender_list.append(gender_calc)
        lap_calc = c['LAP Indicator - 2020-2021'].sum()/len(c)
        lap_list.append(lap_calc)
        sped_total = c['SPED'].sum()
        sped_list.append(sped_total)
        hcp_total = c['HCP - 2020-2021'].sum()
        hcp_list.append(hcp_total)
        irla_calc = c['IRLA-Score - 2020-2021'].sum()/len(c)
        irla_list.append(irla_calc)
        race_int= c['Race'].value_counts()
        racedf = racedf.append(race_int, ignore_index=True)
        racedf = racedf.fillna(0)
        asian_list = racedf['Asian'].values.tolist()
        black_list = racedf['Black'].to_list()
        hispanic_list = racedf['Hispanic'].to_list()
        multi_list = racedf['Multiple'].to_list()
        native_list = racedf['Native'].to_list()
        pi_list = racedf['Pacific Islander'].to_list()
        white_list = racedf['White'].to_list()                      
        g = c.iloc[0]['Grade']
        grade_list.append(g)

    new_calc_df = pd.DataFrame(columns=ALL_CATEGORIES,index=grade_list).rename_axis('Classes')
    new_calc_df['Gender']= gender_list
    new_calc_df['504 - 2020-2021'] = iep_list
    new_calc_df['LAP Indicator - 2020-2021'] = lap_list
    new_calc_df['SPED'] = sped_list
    new_calc_df['HCP - 2020-2021'] = hcp_list
    new_calc_df['Attn % - 2020-2021'] = att_list
    new_calc_df['IRLA-Score - 2020-2021'] = irla_list
    new_calc_df['Asian'] = asian_list
    new_calc_df['Black'] = black_list
    new_calc_df['Hispanic'] = hispanic_list
    new_calc_df['Multiple'] = multi_list
    new_calc_df['Native'] = native_list
    new_calc_df['Pacific Islander'] = pi_list
    new_calc_df['White'] = white_list

    return new_calc_df

def save_xlsx(list_dfs, xlsx_path):
    """Write acceptable classes to Excel file."""

    with ExcelWriter(xlsx_path) as writer:
        i=0
        for x in list_dfs:
            for n, df in enumerate(x):
                df.to_excel(writer,'sheet%s' % i)
                i = i+1
        writer.save()


def main():
    """This program accepts as input a file from a elementary school district's Student Identification System(SIS), randomly assigns student to classes for the next year, performs balance and cluster checking in accordance with user settings, then repeats until all balance and clustering are within tolerance. The program then writes next year's class lists to an Excel file for use by the school. For this prototype, a specific school collaborated with this project, and that school's district uses SIS software distributed by Synergy."""

    # Shuffle students within their grade levels.
    shuffled_stu_by_grade = shuffle(students_by_grade)
    
    # Divide students into classes.
    all_classes_by_grade = divide_into_classes(shuffled_stu_by_grade, cls_per_grade)

    # Fill in missing test scores with average for the class
    cleaned_grades = missing_scores_school(all_classes_by_grade)
    
    # Create dataframes containing calculations for each class
    calc_dfs = calculate(cleaned_grades)
    
    next_yrs_classes = []

    i=0

    # For each grade level, find the class that has the most and least of all binary categories.
    for g in cleaned_grades:
        print('Attempting to solve the outgoing', str(g[0].iloc[0]['Grade']), 'grade...')
        gender_max = calc_dfs[i]['Gender'].max()
        gender_min = calc_dfs[i]['Gender'].min()
        iep_max = calc_dfs[i]['504 - 2020-2021'].max()
        iep_min = calc_dfs[i]['504 - 2020-2021'].min()
        lap_max = calc_dfs[i]['LAP Indicator - 2020-2021'].max()
        lap_min = calc_dfs[i]['LAP Indicator - 2020-2021'].min()
        att_max = calc_dfs[i]['Attn % - 2020-2021'].max()
        att_min = calc_dfs[i]['Attn % - 2020-2021'].min()
        irla_max = calc_dfs[i]['IRLA-Score - 2020-2021'].max()
        irla_min = calc_dfs[i]['IRLA-Score - 2020-2021'].min()
        
        # Check special education and gifted clusters
        cluster_check = check_clusters(calc_dfs[i])
        
        # Check for appropriate race affinity clusters
        affinity_diversity = affinity_diversity_check(calc_dfs[i])
 
        # If all tolerances and clusters are acceptable, save this class to the class list.
        if((math.isclose(gender_max, gender_min, abs_tol = GENDER_TOL)) and (math.isclose(iep_max, iep_min, abs_tol = IEP_TOL)) and (math.isclose(lap_max, lap_min, abs_tol = LAP_TOL)) and (math.isclose(att_max, att_min, abs_tol = ATTENDANCE_TOL)) and (math.isclose(irla_max, irla_min, abs_tol = ATTENDANCE_TOL)) and cluster_check and affinity_diversity):
            next_yrs_classes.append(g)

        # If one tolerance is out of specification, or one category does not have acceptable clustering, repeat shuffling and checking. 
        else:
            while ((math.isclose(gender_max, gender_min, abs_tol = GENDER_TOL)) and (math.isclose(iep_max, iep_min, abs_tol = IEP_TOL)) and (math.isclose(lap_max, lap_min, abs_tol = LAP_TOL)) and (math.isclose(att_max, att_min, abs_tol = ATTENDANCE_TOL)) and  (math.isclose(irla_max, irla_min, abs_tol = ATTENDANCE_TOL)) and cluster_check and affinity_diversity) == False:

                r = reshuffle_one_grade(shuffled_stu_by_grade[i])
                new_classes = divide_one_grade(r, cls_per_grade[i])
                cleaned_grade = missing_scores_gradelevel(new_classes)
                new_calc_df = calculate_one_grade(cleaned_grade)
                
                print('Attempting to solve the outgoing', str(g[0].iloc[0]['Grade']), 'grade for next year...')
                print('Gender balance within tolerance?                                             ', str(math.isclose(gender_max, gender_min, abs_tol = GENDER_TOL)), '                    ', str(g[0].iloc[0]['Grade']))
                print('IEP student balance within tolerance?                                        ', str(math.isclose(iep_max, iep_min, abs_tol = IEP_TOL)), '                    ', str(g[0].iloc[0]['Grade']))
                print('Students with LAP indicator balance within tolerance?                        ', str(math.isclose(lap_max, lap_min, abs_tol = LAP_TOL)), '                    ', str(g[0].iloc[0]['Grade']))
                print('Historical attendance balance within tolerance?                              ', str(math.isclose(att_max, att_min, abs_tol = ATTENDANCE_TOL)), '                    ', str(g[0].iloc[0]['Grade']))
                print('Each class balanced for IRLA scores?                                         ', str(math.isclose(irla_max, irla_min, abs_tol = ATTENDANCE_TOL)), '                    ', str(g[0].iloc[0]['Grade']))
                print('Each class checked for acceptable special education and HiCap clusters?      ', str(cluster_check), '                    ', str(g[0].iloc[0]['Grade']))
                print('Race affinity and diversity checks complete?                                 ', str(affinity_diversity), '                    ', str(g[0].iloc[0]['Grade']))

                gender_max = new_calc_df['Gender'].max()
                gender_min = new_calc_df['Gender'].min()
                iep_max = new_calc_df['504 - 2020-2021'].max()
                iep_min = new_calc_df['504 - 2020-2021'].min()
                lap_max = new_calc_df['LAP Indicator - 2020-2021'].max()
                lap_min = new_calc_df['LAP Indicator - 2020-2021'].min()
                att_max = new_calc_df['Attn % - 2020-2021'].max()
                att_min = new_calc_df['Attn % - 2020-2021'].min()
                irla_max = new_calc_df['IRLA-Score - 2020-2021'].max()
                irla_min = new_calc_df['IRLA-Score - 2020-2021'].min()
                cluster_check = check_clusters(new_calc_df)
                affinity_diversity = affinity_diversity_check(new_calc_df)

            """TODO unclean final classes by unfilling missing test scores so school will have correct data (missing test scores) in their new class lists"""

            next_yrs_classes.append(new_classes)
        i = i+1 
    
    s = ("Congratulations! Your classes have been formed with the following tolerances: \n"
            "Every class within each grade level has within " + (str(GENDER_TOL*100)) + "% the same number of boys.\n"
            "Every class within each grade level has within " + (str(IEP_TOL*100)) + "% the same number of students who have an IEP. \n"
            "Every class within each grade level has within " + (str(LAP_TOL*100)) + "% the same number of students who have a Learning Acquisition Plan indicator. \n"
            "After grouping attendance into three categories (Above 90%, 90-80%, and below 80%), every class within each grade level has a distribution of students in these categories within " + (str(ATTENDANCE_TOL*100)) + "%. \n"
            "Every class within each grade level has balanced achievement. The average of students' standardized test scores for each class is within " + (str(IRLA_TOL*100)) + "%. \n"
            "All special education and highly capable students are clustered in accordance with your cluster file, and students' races are balanced across classrooms with special affinity groups assigned in accordance with your cluster file. \n")

    print(s)
    save_xlsx(next_yrs_classes, r'C:\Users\derek\Documents\CityU\CS687_Capstone\Classroom Equity Folder\NextYrsClasses.xlsx' )

# Clean data and divide students by grade 
students_by_grade = initialize_data()

# Determine how many classes each grade level will form for next year.
cls_per_grade = how_many_classes(students_by_grade)

main()