# Design Principles

## Documentation

Add docstring when relevant

## Test Safety Net Before Changing Code

Add full non-regression test coverage for existing behaviour before modifying or
refactoring it. Tests must pass before any code change begins.

## Refactor in a Separate Commit

Refactoring is proposed first, agreed on, then committed independently from
feature work. This keeps the history readable and makes regressions easy to
bisect.

## Propose Architecture and Dependencies Before Acting

Do not introduce new abstractions, architectural patterns, or external
dependencies unilaterally. Raise the proposal and wait for agreement.

## Single Source of Truth for Related Data

Keep related fields together in one structure rather than across parallel
collections. For example, order fields (`sku`, `qty`, `status`) belong in one
`Order` object, not three separate dicts keyed by the same ID.

## Named Constants Over Magic Strings

Use enums or named constants instead of raw string literals for domain values
(e.g. order statuses). This makes invalid states unrepresentable and mistakes
detectable at the call site.

## One Responsibility Per Method

A method should do one thing. A dispatcher routes to handlers; each handler
executes one command. Mixing routing, business logic, and I/O in a single method
is a smell.

## No Dead Code

Remove unused variables, redundant initialisation, and unreachable branches.
Code that does nothing is noise that increases cognitive load.

## Keep It Simple

Write the minimum code that satisfies the requirement. Avoid speculative
abstractions, premature generalisations, and defensive code for scenarios that
cannot occur.

## Self-Review After Every Change

After each change, review the diff for correctness, clarity, and adherence to
these principles before committing.
