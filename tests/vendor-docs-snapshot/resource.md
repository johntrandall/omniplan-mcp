# Resource and Assignment Classes
Source: https://omni-automation.com/omniplan/resources.html (captured 2026-05-01)

## Resource — Properties
- assignments
- completedCost
- costPerHour
- costPerUse
- efficiency
- email
- members
- name
- note
- schedule
- totalCost
- totalHours
- type
- uniqueID
- unitsAvailable

## Resource — Methods
- addMember
- descendents
- remove

## Assignment — Properties
Per the OmniPlan 4 omniJS docs, the Assignment class exposes:
- resource
- task
- unitsAssigned
- effort
- effortRemaining
- effortDone
- startDate
- endDate
- isCompleted

## Assignment — Methods
- remove

## ResourceType enum values
- ResourceType.all
- ResourceType.equipment
- ResourceType.group
- ResourceType.material
- ResourceType.staff

## ResourceAssignmentType enum values
- ResourceAssignmentType.adjustAssignedUnits
- ResourceAssignmentType.adjustDuration
- ResourceAssignmentType.adjustEffort
- ResourceAssignmentType.all
