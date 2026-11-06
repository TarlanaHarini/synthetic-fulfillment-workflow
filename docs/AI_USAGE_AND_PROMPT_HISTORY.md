# AI Usage and Prompt History

## 1. AI Tools Used

The following AI tools assisted during project development:

- **ChatGPT:** Used for understanding requirements, planning milestones, explaining technical concepts, reviewing outputs, preparing documentation, and debugging guidance.
- **Codex:** Used for codebase inspection, implementation assistance, code changes, test execution, and validation of the fulfillment workflow.

AI assistance was used as a development aid. Generated code and recommendations were reviewed through project tests, output inspection, and validation reports.

## 2. Prompt History

The following is a summary of the actual prompts and instructions used during development. It is a reconstructed summary, not a verbatim export of every conversation.

### A. Understanding the Requirements

The project requirements were provided to AI to understand the fulfillment workflow, required entities, relationships, dataset sizes, business rules, anomaly cases, and acceptance criteria.

### B. Schema Review

AI was instructed to inspect the existing SQLite schema, verify required entities and relationships, identify missing constraints and indexes, and make only necessary Milestone 1 corrections.

### C. Workflow Implementation

Codex was instructed to inspect the repository and implement the remaining milestones in sequence, including:

- Deterministic synthetic data generation.
- Inventory and warehouse capacity-based allocation.
- Partial allocation and split shipments.
- Carrier and service-level compatibility.
- Business-day delivery promises.
- Shipment and tracking event generation.
- Ground-truth anomaly examples.
- Validation, evaluation metrics, and CSV/JSON/SQL exports.
- Documentation and automated tests.

### D. Debugging and Validation

AI was asked to investigate and correct issues identified during implementation, including allocation bookkeeping, split shipment metrics, anomaly input separation, and insufficient inventory and capacity constraints.

### E. Final Review

ChatGPT was used to interpret acceptance and evaluation reports, check the five anomaly examples, review README instructions, understand test results, and prepare the submission documentation.

## 3. Where AI Accelerated Development

AI assistance was particularly useful for:

- Breaking a large problem statement into manageable milestones.
- Designing the data generation and validation workflow.
- Implementing repetitive data generation and export logic.
- Identifying inconsistencies in allocation and reporting.
- Creating test cases and documentation.
- Explaining evaluation metrics and debugging results.

## 4. Areas With Heavy AI Assistance

Codex provided substantial implementation assistance for the synthetic data generator, allocation workflow, promise calculation, shipment tracking, anomaly inputs, validation logic, and export functionality.

ChatGPT also provided substantial assistance with planning, interpreting requirements, reviewing reported results, and preparing technical explanations.

I do not claim that all implementation code was independently written by me.

## 5. My Personal Involvement and Verification

My involvement included:

- Providing and reviewing the project requirements.
- Following the development milestones and reviewing implementation updates.
- Running the automated test suite locally.
- Inspecting the acceptance report and evaluation metrics.
- Checking all five ground-truth anomaly examples and their corresponding anomaly inputs.
- Reviewing the README and project documentation.
- Initializing Git, preparing `.gitignore`, committing the project, and uploading it to a public GitHub repository.

I personally ran:

```powershell
python -m unittest discover -s tests -v
```

The observed result was six passing tests and no test failures.

I also reviewed the reported full-dataset results, including 50,000 orders, 100,000 tracking events, SQLite integrity status, and foreign-key validation.

## 6. What I Learned

Through this project, I gained practical understanding of:

- Relational database design and foreign-key relationships.
- Synthetic data generation and reproducibility.
- Inventory allocation and warehouse capacity constraints.
- Split shipment handling.
- Delivery promise calculations.
- Shipment tracking and lifecycle validation.
- Automated testing and evaluation metrics.
- Git and GitHub project management.
- Reviewing and validating AI-generated code rather than relying on generated output without testing.

## 7. Transparency Statement

AI tools were used during planning, implementation, debugging, testing support, and documentation.

The implementation involved substantial AI-generated and AI-assisted code. I reviewed the available test results, generated reports, anomaly examples, and repository contents. I understand that passing the included tests does not guarantee that every possible business scenario is handled correctly.

The project uses synthetic data and simulated carrier behavior. It is an educational workflow implementation, not a live production fulfillment integration.dir docs