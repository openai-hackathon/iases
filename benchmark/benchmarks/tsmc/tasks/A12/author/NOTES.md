# Author notes

Design difficulty: medium. Replace a two-line static join with revision visibility, tombstone and quality precedence, event-time selection and independent calibration-time semantics across three modules. Medium difficulty remains bounded to exact relational selection; unlike the revised hydraulic task it has no continuous interval reconstruction or publication retractions.

Family: `revisioned_bitemporal_metrology_join`. References: nist-sms.

Fixtures are newly authored. No external dataset rows are redistributed.
