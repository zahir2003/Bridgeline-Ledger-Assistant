# Evaluation

## Evaluation Goal

The evaluation checks whether the assistant gives correct and traceable
answers for the required ledger questions.

The project separates:

1.  **Intent understanding** --- handled by the local Ollama model.
2.  **Financial calculation** --- handled deterministically by Python.

Therefore, application-level financial correctness is primarily
evaluated against deterministic Python ground truth.

------------------------------------------------------------------------

## Required Questions

  --------------------------------------------------------------------------------------
  ID             Question       Expected / Hand Answer    Tool Answer     Result
  -------------- -------------- ------------------------- --------------- --------------
  Q1             What is the    ₹4,789,316.32             ₹4,789,316.32   PASS
                 total payable                                            
                 amount for                                               
                 Bharat Steel                                             
                 Works?                                                   

  Q2             Which invoices 20 invoices               20 invoices     PASS
                 were overdue                                             
                 as of 31 March                                           
                 2025?                                                    

  Q3             Which vendor   Konark Fabrication Pvt.   Same            PASS
                 has the        Ltd. --- ₹6,402,037.70                    
                 highest spend?                                           

  Q4             Which invoices 24 invoices               24 invoices     PASS
                 have taxable                                             
                 value above ₹5                                           
                 lakh?                                                    

  Q5             What is the    ₹874,943.73               ₹874,943.73     PASS
                 total GST for                                            
                 Q3?                                                      

  Q6             Which invoices 5 exceptions              5 exceptions    PASS
                 have ITC                                                 
                 issues and                                               
                 why?                                                     

  Q7             What is the    -8.16 days                -8.16 days      PASS
                 average                                                  
                 payment delay                                            
                 for                                                      
                 Fabrication                                              
                 invoices?                                                

  Q8             Are there any  Data-quality findings     Same findings   PASS
                 duplicate or   including duplicate,                      
                 suspicious     future invoice,                           
                 entries?       payment-before-invoice,                   
                                missing taxable, missing                  
                                GSTIN and GST mismatch                    
  --------------------------------------------------------------------------------------

------------------------------------------------------------------------

## Additional Questions

  -------------------------------------------------------------------------------
  ID             Question        Expected / Hand    Tool Answer    Result
                                 Answer                            
  -------------- --------------- ------------------ -------------- --------------
  Q9             What is the     Konark Fabrication Same           PASS
                 highest-spend   Pvt. Ltd. ---                     
                 vendor?         ₹6,402,037.70                     

  Q10            Which invoices  5 policy-supported Same 5         PASS
                 have GST/ITC    ITC exceptions     exceptions     
                 problems?                                         

  Q11            How many        24                 24             PASS
                 invoices have                                     
                 taxable value                                     
                 above ₹5 lakh?                                    

  Q12            What is the     -8.16 days         -8.16 days     PASS
                 average                                           
                 Fabrication                                       
                 payment delay?                                    
  -------------------------------------------------------------------------------

These additional questions intentionally test paraphrases of supported
intents rather than adding unsupported financial logic.

------------------------------------------------------------------------

## Output Traceability

The application returns source rows for the financial result.

Examples:

-   Bharat total → source rows are printed.
-   Highest-spend vendor → source rows are printed.
-   Overdue invoices → each invoice has a source row.
-   ITC exceptions → each exception has a source row.
-   Data-quality findings → affected source rows are printed.

This allows the user to trace results back to the original ledger.

------------------------------------------------------------------------

## Model Benchmark

Two local Ollama models were tested:

  Model             Approx. Model Size   Observed Generation Speed
  --------------- -------------------- ---------------------------
  llama3:latest                 4.7 GB          \~10.71 tokens/sec
  llama3.2:3b                   2.0 GB          \~41.11 tokens/sec

The benchmark was run locally and should be treated as a
machine-specific observation, not a universal model speed claim.

------------------------------------------------------------------------

## Application Accuracy

The tested required questions produced correct deterministic financial
results.

A high application accuracy is expected because:

``` text
LLM
 ↓
Intent
 ↓
Python calculation
 ↓
Ground-truth result
```

The LLM is not generating the financial numbers.

Therefore, a high application-level score does not mean the LLM itself
can reliably perform financial arithmetic. It means the architecture
successfully limits the LLM's role.

------------------------------------------------------------------------

## Honest Evaluation Notes

The evaluation should not claim that the LLM is perfect at every
possible question.

Important limitations:

-   Only the supported intents are evaluated.
-   The test set is small.
-   Model intent classification can fail on unusual wording.
-   Financial correctness depends on the deterministic Python rules and
    the quality of the input ledger.
-   The benchmark timings are local observations and can vary between
    runs and machines.

The assistant also intentionally rejects unsupported questions rather
than hallucinating an answer.

Example:

``` text
python -m src.main "question"
```

returns:

``` text
Sorry, I could not understand the question or it is not currently supported.
```

This is treated as safe behavior, not a financial-answer failure.

------------------------------------------------------------------------

## Final Evaluation

**Overall result: PASS**

The required questions were checked against deterministic expected
results, and the CLI returned the expected financial values, invoice
lists, exceptions, source rows, and policy explanations.
