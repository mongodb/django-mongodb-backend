================================
AI-Generated Contribution Policy
================================

Our Stance
----------

We only accept pull requests that are authored and submitted by human
contributors who fully understand the changes they are proposing. Pull requests
that are not clearly owned and understood by a human contributor may be closed.
**All contributions must be submitted, reviewed, and understood by human
contributors.**

Why This Policy Exists
----------------------

At MongoDB, we understand the power and prevalence of AI tools in software
development. With that being said, many MongoDB libraries are foundational
tools used in production systems worldwide. The nature of these libraries
requires:

- **Deep domain expertise**: Django MongoDB Backend bridges Django's ORM and
  MongoDB. The aggregation pipeline compilation, query generation, migration
  system, and connection management require an understanding that AI alone
  cannot substantiate.

- **Long-term maintainability**: Contributors need to be able to explain *why*
  code is written a certain way, explain design decisions, and be available to
  iterate on their contributions.

- **Security responsibility**: Query generation, authentication handling, and
  data serialization cannot be left to probabilistic code generation.

What This Means for Contributors
---------------------------------

**Required:**

- A full understanding of every line of code you submit.
- The ability to explain and defend your implementation choices.
- A willingness to iterate and maintain your contributions.

**Encouraged:**

- Using AI assistants as learning tools to understand concepts.
- IDE autocomplete features that suggest standard patterns.
- AI help for brainstorming approaches (but write the code yourself).
- Writing code using AI tools, reviewing each line and revising code as
  necessary.

**Not allowed:**

- Submitting PRs generated solely by AI tools.
- Copy-pasting AI-generated code without full understanding.

Disclosure
----------

If you used AI assistance in any way during your contribution, please disclose
what the AI assistant was used for in your PR description. We would love to
know what tools developers have found useful in their development process.

Questions?
----------

If you're unsure whether your contribution complies with this policy, please
ask for guidance within the PR and clarify any uncertainty. We're happy to
guide contributors toward successful contributions.

.. note::

   This policy helps us maintain the reliability, security, and trustworthiness
   that production applications depend on. Thank you for understanding and for
   contributing thoughtfully to Django MongoDB Backend.
