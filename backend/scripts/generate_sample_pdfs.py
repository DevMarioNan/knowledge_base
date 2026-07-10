"""Generate sample clinical trial PDF documents for E2E testing."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(HERE, "..", "test_samples")

try:
    from fpdf import FPDF
except ImportError:
    print("Installing fpdf2...")
    os.system(f"{sys.executable} -m pip install fpdf2 -q")
    from fpdf import FPDF


class TrialPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 8, "TrialBase - Clinical Trial Document", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, text)
        self.ln(2)


def make_study_protocol() -> FPDF:
    pdf = TrialPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Phase 3 Study of Xanomeline-Trospium", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Protocol Number: CT-2024-001", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Sponsor: NeuroPharma Therapeutics", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section("1. Background and Rationale")
    pdf.body_text(
        "Alzheimer's disease is a progressive neurodegenerative disorder affecting approximately 6.5 million "
        "adults in the United States. Current symptomatic treatments, including acetylcholinesterase inhibitors, "
        "provide modest benefit but are associated with significant gastrointestinal side effects. "
        "Xanomeline is a muscarinic acetylcholine receptor agonist that has demonstrated cognitive benefits "
        "in prior clinical trials, but its development was limited by cholinergic side effects. "
        "Trospium is a peripherally-restricted muscarinic antagonist that does not cross the blood-brain barrier, "
        "which may mitigate peripheral cholinergic adverse events when co-administered with xanomeline."
    )

    pdf.section("2. Study Objectives")
    pdf.body_text(
        "Primary Objective: To evaluate the efficacy of xanomeline-trospium combination therapy compared to "
        "placebo on cognitive function in patients with mild-to-moderate Alzheimer's disease, as measured by "
        "change from baseline on the Alzheimer's Disease Assessment Scale-Cognitive Subscale (ADAS-Cog) at Week 24."
    )
    pdf.body_text(
        "Secondary Objectives: (1) To evaluate the effect of xanomeline-trospium on global clinical status "
        "as measured by the Clinician's Interview-Based Impression of Change Plus Caregiver Input (CIBIC+); "
        "(2) To evaluate the effect on activities of daily living using the Alzheimer's Disease Cooperative Study "
        "- Activities of Daily Living Inventory (ADCS-ADL); (3) To assess the safety and tolerability profile."
    )

    pdf.section("3. Study Design")
    pdf.body_text(
        "This is a multicenter, randomized, double-blind, placebo-controlled, parallel-group Phase 3 study. "
        "Approximately 800 patients will be randomized in a 1:1 ratio to receive either xanomeline-trospium "
        "combination therapy or matching placebo for 24 weeks of double-blind treatment, followed by a "
        "28-week open-label extension period. Randomization will be stratified by disease severity (mild vs. moderate) "
        "and concomitant use of cholinesterase inhibitors (yes vs. no)."
    )

    pdf.section("4. Inclusion Criteria")
    pdf.body_text(
        "1. Male or female patients aged 50-85 years inclusive. "
        "2. Diagnosis of probable Alzheimer's disease per NIA-AA criteria. "
        "3. Mini-Mental State Examination (MMSE) score of 14-26 inclusive at screening. "
        "4. Rosen Modified Hachinski Ischemic Score <= 4. "
        "5. Stable doses of cholinesterase inhibitors for at least 3 months prior to screening, if applicable. "
        "6. Study partner available who has at least 10 hours per week of contact with the patient. "
        "7. Written informed consent obtained from patient or legally authorized representative."
    )

    pdf.section("5. Exclusion Criteria")
    pdf.body_text(
        "1. Current diagnosis of any other form of dementia. "
        "2. Evidence of clinically relevant cerebrovascular disease. "
        "3. Major depressive episode within the past 6 months. "
        "4. History of alcohol or substance abuse within the past 2 years. "
        "5. Clinically significant hepatic or renal impairment. "
        "6. Use of anticholinergic medications with significant central nervous system activity. "
        "7. History of seizures or epilepsy. "
        "8. Participation in any other interventional clinical trial within 30 days prior to screening."
    )

    pdf.section("6. Statistical Considerations")
    pdf.body_text(
        "The primary efficacy analysis will be performed using a mixed model for repeated measures (MMRM) "
        "on the change from baseline in ADAS-Cog score at Week 24. The analysis will include treatment group, "
        "visit, stratification factors, and treatment-by-visit interaction as fixed effects, with baseline "
        "ADAS-Cog score as a covariate. A sample size of 800 patients (400 per arm) provides approximately 90% "
        "power to detect a treatment difference of 2.5 points on ADAS-Cog at Week 24, assuming a standard "
        "deviation of 8 points and a two-sided alpha level of 0.05."
    )

    return pdf


def make_consent_form() -> FPDF:
    pdf = TrialPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Informed Consent Form", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Study: Phase 3 Xanomeline-Trospium in Alzheimer's Disease", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "IRB Protocol Number: CT-2024-001-ICF", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section("Purpose of the Study")
    pdf.body_text(
        "You are being asked to take part in a research study to evaluate whether the combination of two "
        "study medications, xanomeline and trospium, can improve cognitive function in patients with "
        "Alzheimer's disease. Xanomeline is an investigational drug that targets muscarinic receptors in "
        "the brain, potentially improving memory and thinking. Trospium is an FDA-approved medication for "
        "overactive bladder that may help reduce certain side effects of xanomeline."
    )

    pdf.section("Study Procedures")
    pdf.body_text(
        "If you agree to participate, the study will last approximately 52 weeks (24 weeks of double-blind "
        "treatment plus 28 weeks of open-label extension). You will be asked to attend 12-14 clinic visits. "
        "At each visit, you will undergo cognitive assessments, physical examinations, vital sign measurements, "
        "ECGs, and blood laboratory tests. Study medication will be taken orally twice daily with food."
    )

    pdf.section("Risks and Discomforts")
    pdf.body_text(
        "The most common side effects of xanomeline include gastrointestinal symptoms such as nausea, "
        "vomiting, diarrhea, and abdominal pain. Trospium may cause dry mouth, constipation, and urinary "
        "retention. There is a risk of falls, particularly in elderly patients. All medications will be "
        "monitored by the study physician. You should report any side effects to the study team immediately."
    )

    pdf.section("Confidentiality")
    pdf.body_text(
        "Your study records will be kept confidential to the extent permitted by law. Your identity will "
        "be coded using a unique patient identification number. Data will be stored in secure, password-protected "
        "databases accessible only to authorized study personnel. Results may be published in medical journals "
        "but your identity will not be disclosed."
    )

    return pdf


def make_safety_report() -> FPDF:
    pdf = TrialPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Clinical Safety Report - Interim Analysis", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Data Monitoring Committee Report #3", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Date: March 15, 2025", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section("1. Summary")
    pdf.body_text(
        "This interim safety report summarizes adverse events reported during the first 12 weeks of the "
        "Phase 3 study of xanomeline-trospium in Alzheimer's disease. As of the data cutoff date, 450 patients "
        "have been enrolled and randomized (225 active, 225 placebo). The independent Data Monitoring Committee "
        "has reviewed all available safety data."
    )

    pdf.section("2. Adverse Events Overview")
    pdf.body_text(
        "A total of 312 adverse events (AEs) were reported: 198 in the active treatment group and 114 in "
        "the placebo group. The majority of AEs were mild to moderate in severity. The most frequently "
        "reported AEs in the active group were nausea (22.7%), vomiting (14.2%), diarrhea (11.1%), and "
        "dizziness (8.9%). Five serious adverse events (SAEs) were reported: 3 in the active group "
        "(one hospitalization for pneumonia, one fall with hip fracture, one case of syncope) and 2 in "
        "the placebo group (one hospitalization for CHF exacerbation, one case of atrial fibrillation)."
    )

    pdf.section("3. Laboratory Findings")
    pdf.body_text(
        "No clinically significant differences were observed between treatment groups in hematology or "
        "clinical chemistry parameters. Transient elevations in liver transaminases (ALT/AST > 3x ULN) "
        "were observed in 4 patients (1.8%) in the active group and 2 patients (0.9%) in the placebo group. "
        "All elevations resolved without intervention. No Hy's Law cases were identified."
    )

    pdf.section("4. Vital Signs and ECG")
    pdf.body_text(
        "Mean changes in systolic blood pressure were +2.1 mmHg (active) vs. -0.5 mmHg (placebo). "
        "No clinically meaningful changes in heart rate, respiratory rate, or body temperature were observed. "
        "ECG evaluations showed no evidence of QTc prolongation or other clinically significant "
        "arrhythmogenic signals in either treatment group."
    )

    pdf.section("5. DMC Recommendation")
    pdf.body_text(
        "Based on the available safety data, the Data Monitoring Committee recommends that the study "
        "continue without modification. The safety profile is consistent with the known pharmacology of "
        "the study medications, and no unexpected safety signals have been identified. The risk-benefit "
        "assessment remains favorable for continued enrollment."
    )

    return pdf


def make_efficacy_analysis() -> FPDF:
    pdf = TrialPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Statistical Analysis Plan", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Efficacy Analysis Plan - Xanomeline-Trospium Phase 3", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Document Version: 2.1, dated January 10, 2025", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section("1. Primary Analysis")
    pdf.body_text(
        "The primary endpoint is the change from baseline to Week 24 in the Alzheimer's Disease Assessment "
        "Scale-Cognitive Subscale (ADAS-Cog) total score. The primary analysis will be conducted using a "
        "Mixed Model for Repeated Measures (MMRM) approach. The model will include fixed effects for "
        "treatment group, visit week, treatment-by-visit interaction, and stratification factors (disease "
        "severity and concomitant cholinesterase inhibitor use). Baseline ADAS-Cog score will be included "
        "as a continuous covariate. An unstructured covariance matrix will be used to model the within-patient "
        "correlation. Kenward-Roger approximation will be used for denominator degrees of freedom."
    )

    pdf.section("2. Sensitivity Analyses")
    pdf.body_text(
        "Several sensitivity analyses will be performed: (1) Pattern-mixture model to assess the impact of "
        "missing data under non-ignorable missingness assumptions; (2) Analysis using multiple imputation "
        "under missing at random (MAR) assumption; (3) Analysis of completers only (patients who complete "
        "Week 24 assessment); (4) Analysis using tipping-point approach to determine how much the treatment "
        "effect would need to shift to lose statistical significance."
    )

    pdf.section("3. Subgroup Analyses")
    pdf.body_text(
        "Pre-specified subgroup analyses will be performed for the following factors: age group (50-64, "
        "65-74, 75-85 years), disease severity (mild MMSE 20-26 vs. moderate MMSE 14-19), APOE4 carrier "
        "status (carrier vs. non-carrier), sex (male vs. female), and concomitant cholinesterase inhibitor "
        "use (yes vs. no). These analyses will be performed using the same MMRM model with the addition of "
        "subgroup-by-treatment interaction terms."
    )

    pdf.section("4. Multiplicity Adjustment")
    pdf.body_text(
        "To control the family-wise Type I error rate at 0.05 across the primary and key secondary endpoints, "
        "a hierarchical testing procedure will be employed. The testing sequence is: (1) ADAS-Cog at Week 24 "
        "(primary), (2) CIBIC+ at Week 24, (3) ADCS-ADL at Week 24, (4) MMSE at Week 24. Each endpoint will "
        "be tested at the two-sided 0.05 level only if all preceding endpoints in the hierarchy are significant."
    )

    return pdf


def make_investigator_brochure() -> FPDF:
    pdf = TrialPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Investigator's Brochure (Abridged)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Xanomeline-Trospium Combination Therapy", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Edition 4.0, December 2024", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.section("1. Introduction")
    pdf.body_text(
        "Xanomeline is a potent muscarinic acetylcholine receptor agonist with high affinity for M1 and M4 "
        "receptor subtypes. Unlike cholinesterase inhibitors, which indirectly increase acetylcholine levels, "
        "xanomeline directly stimulates muscarinic receptors. Preclinical studies have shown that M1 receptor "
        "activation enhances cognitive function through modulation of hippocampal and cortical neural circuits. "
        "M4 receptor activation may reduce psychotic symptoms common in Alzheimer's disease."
    )

    pdf.section("2. Pharmacokinetics")
    pdf.body_text(
        "Following oral administration, xanomeline reaches peak plasma concentrations in 1-2 hours. "
        "The elimination half-life is approximately 4-6 hours. Steady-state concentrations are achieved "
        "within 3-5 days of twice-daily dosing. Xanomeline is extensively metabolized by CYP2D6 and CYP3A4 "
        "with less than 1% excreted unchanged in urine. Trospium, when co-administered, does not significantly "
        "affect xanomeline pharmacokinetics. Food intake reduces the rate but not the extent of xanomeline absorption."
    )

    pdf.section("3. Preclinical Safety")
    pdf.body_text(
        "In preclinical toxicology studies, the primary findings were related to the peripheral cholinergic "
        "effects of xanomeline. In rats, doses up to 30 mg/kg/day for 6 months showed evidence of "
        "gastrointestinal irritation at the highest dose. No carcinogenic potential was identified in "
        "2-year bioassays. Reproductive toxicity studies showed no evidence of teratogenicity at clinically "
        "relevant exposures. Cardiovascular safety pharmacology studies demonstrated no effects on hERG "
        "channel current or cardiac action potential duration at concentrations up to 10 microM."
    )

    return pdf


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    documents = [
        ("study_protocol.pdf", make_study_protocol()),
        ("consent_form.pdf", make_consent_form()),
        ("safety_report.pdf", make_safety_report()),
        ("efficacy_analysis.pdf", make_efficacy_analysis()),
        ("investigator_brochure.pdf", make_investigator_brochure()),
    ]

    for filename, pdf in documents:
        filepath = os.path.join(OUTPUT_DIR, filename)
        pdf.output(filepath)
        size = os.path.getsize(filepath)
        print(f"  {filename}  ({size / 1024:.1f} KB)")

    print(f"\n{len(documents)} sample PDFs generated in: {OUTPUT_DIR}")
