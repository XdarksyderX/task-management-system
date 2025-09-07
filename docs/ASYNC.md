# Async Event System

## 📋 Overview

The Task Management System uses **async events** with **Apache Kafka** to handle communication between services and track all system activities.

## 🏗️ Architecture

### **Kafka Topics**
- **`user-activities`** - User actions (create, update, delete)
- **`task-events`** - Task-specific events
- **`analytics-events`** - Events for analysis and metrics
- **`system-notifications`** - System notifications

### **Publishers**
- **Django Backend** - Publishes `user-activities` and `task-events`
- **Flask Analytics** - Publishes `analytics-events`

### **Consumers**
- **Django Backend** - Consumes events for notifications and updates
- **Flask Analytics** - Consumes events for metrics and analysis
- **Notification System** - Consumes events for alerts

---

## 📊 Events by Topic

### 🎯 **`user-activities` Topic**

#### **Task Events**
| Action | Event | Description |
|--------|--------|-------------|
| Create task | `task_created` | New task created |
| Update task | `task_updated` | Task modified |
| Delete task | `task_deleted` | Task deleted |

#### **Team Events**
| Action | Event | Description |
|--------|--------|-------------|
| Create team | `team_created` | New team created |
| Update team | `team_updated` | Team modified |
| Delete team | `team_deleted` | Team deleted |

#### **Tag Events**
| Action | Event | Description |
|--------|--------|-------------|
| Create tag | `tag_created` | New tag created |
| Update tag | `tag_updated` | Tag modified |
| Delete tag | `tag_deleted` | Tag deleted |

#### **User Events**
| Action | Event | Description |
|--------|--------|-------------|
| Register user | `user_created` | New user registered |
| Update user | `user_updated` | User modified |

#### **Task Template Events**
| Action | Event | Description |
|--------|--------|-------------|
| Create template | `task_template_created` | New template created |
| Update template | `task_template_updated` | Template modified |
| Delete template | `task_template_deleted` | Template deleted |

---

### 📈 **`analytics-events` Topic**

#### **Dashboard Events**
| Action | Event | Description |
|--------|--------|-------------|
| View dashboard | `dashboard_viewed` | User accesses dashboard |
| View distribution | `task_distribution_viewed` | User sees task distribution |

#### **Report Events**
| Action | Event | Description |
|--------|--------|-------------|
| Generate report | `report_generated` | Report requested |
| Download report | `report_downloaded` | Report downloaded |

#### **Query Events**
| Action | Event | Description |
|--------|--------|-------------|
| Analytics query | `analytics_query` | Any analytics query |

#### **User Events**
| Action | Event | Description |
|--------|--------|-------------|
| View user stats | `user_stats_accessed` | User statistics viewed |
| View team performance | `team_performance_accessed` | Team performance viewed |

#### **Error Events**
| Action | Event | Description |
|--------|--------|-------------|
| System error | `error_occurred` | Error in any component |

---

### 🔧 **`task-events` Topic**

#### **Task Events (Detailed)**
| Action | Event | Description |
|--------|--------|-------------|
| Change status | `task_status_changed` | Task status modified |
| Change priority | `task_priority_changed` | Task priority modified |
| Assign task | `task_assigned` | Task assigned to user |
| Set due date | `task_due_date_set` | Due date set |
| Archive task | `task_archived` | Task archived |
| Complete task | `task_completed` | Task marked as completed |

#### **Task Tag Events**
| Action | Event | Description |
|--------|--------|-------------|
| Add tag | `task_tag_added` | Tag added to task |
| Remove tag | `task_tag_removed` | Tag removed from task |

#### **Comment Events**
| Action | Event | Description |
|--------|--------|-------------|
| Add comment | `comment_added` | Comment added to task |
| Edit comment | `comment_edited` | Comment edited |
| Delete comment | `comment_deleted` | Comment deleted |

---

### 📢 **`system-notifications` Topic**

#### **System Events**
| Action | Event | Description |
|--------|--------|-------------|
| System error | `system_error` | Critical system error |
| Maintenance | `system_maintenance` | System under maintenance |
| Backup completed | `backup_completed` | Backup finished |

---

## 📋 Event Structure

### **Standard Format**
```json
{
  "event_type": "task_created",
  "user_id": 123,
  "timestamp": "2025-09-07T10:30:00Z",
  "data": {
    "task_id": 456,
    "title": "Implement login",
    "status": "todo",
    "priority": "high",
    "action": "created"
  },
  "metadata": {
    "source": "django_backend",
    "version": "1.0"
  }
}
```

### **Common Fields**
- **`event_type`**: Specific event type
- **`user_id`**: ID of user who performed action
- **`timestamp`**: Date and time in ISO 8601 format
- **`data`**: Event-specific information
- **`metadata`**: Additional information (optional)

---

## 🔄 Event Flow

### **1. Task Creation**
```
User creates task → Django Signal → EventPublisher → Kafka (user-activities)
                    ↓
Analytics consume → Update metrics → Dashboard updated
                    ↓
Notifications → Send team notification
```

### **2. Status Update**
```
User changes status → Django Signal → EventPublisher → Kafka (task-events)
                      ↓
WebSocket → Real-time notification
                      ↓
Analytics → Update speed metrics
```

### **3. Analytics Query**
```
User views dashboard → Flask Analytics → EventPublisher → Kafka (analytics-events)
                       ↓
Analytics consume → Usage metrics → Activity reports
```

---

## ⚙️ Configuration

### **Environment Variables**
```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ENABLED=1

# Event Publisher
EVENT_PUBLISHER_TYPE=kafka  # kafka, memory

# Topics
USER_ACTIVITIES_TOPIC=user-activities
TASK_EVENTS_TOPIC=task-events
ANALYTICS_EVENTS_TOPIC=analytics-events
```

### **Docker Dependencies**
```yaml
services:
  web:
    depends_on:
      kafka:
        condition: service_healthy

  analytics:
    depends_on:
      kafka:
        condition: service_healthy
```


## 🚨 Error Handling

### **Fallback Strategy**
1. **Kafka available** → Publish normally
2. **Kafka unavailable** → Fallback to Memory Publisher
3. **Memory Publisher** → Store in memory (development)
4. **Critical error** → Detailed logging + alerts
