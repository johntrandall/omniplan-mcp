# Task Class
Source: https://omni-automation.com/omniplan/tasks.html (captured 2026-05-01, OmniPlan 4.10.2)

## Properties
- absoluteEndLimit
- absoluteStartLimit
- assignments
- assignmentsCost
- currentEndLimit
- currentStartLimit
- dependents
- duration
- effort
- effortDone
- effortRemaining
- endDate
- endNoEarlierThanDate
- endNoLaterThanDate
- expectedEffortEstimate
- freeSlack
- manualEndDate
- manualStartDate
- lockedEndDate
- lockedStartDate
- maxEffortEstimate
- minEffortEstimate
- note
- prerequisites
- priority
- resourceAssignmentType
- resourceLeveledDate
- resourceLevelingDelay
- startDate
- startNoEarlierThanDate
- startNoLaterThanDate
- staticCost
- subtasks
- title
- totalCost
- totalSlack
- type
- uniqueID

## Methods
- customValue
- setCustomValue
- descendents
- clearResourceLeveledDate
- addPrerequisite
- addDependent
- addAssignment
- addSubtask
- split
- remove

## TaskType enum values
- TaskType.task
- TaskType.milestone
- TaskType.group
- TaskType.hammock
- TaskType.all
