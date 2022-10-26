# Assumptions
- No failures in the initialization; we assume the initialization is fully complete before any proposals are sent
- There is always at least one learner; the n-1st node will always be given the role learner
- Machines are all on the same network (hostname is always "localhost")

- Possible bug w/ backoff taking a long time