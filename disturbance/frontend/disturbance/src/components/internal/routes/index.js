import InternalDashboard from '../dashboard.vue'
import Search from '../search.vue'
import OrgAccessTable from '../organisations/dashboard.vue'
import OrgAccess from '../organisations/access.vue'
import Organisation from '../organisations/manage.vue'
import Proposal from '../proposals/proposal.vue'
import Referral from '../referrals/referral.vue'
import ApprovalDash from '../approvals/dashboard.vue'
export default
{
    path: '/internal',
    component:
    {
        render(c)
        {
            return c('router-view')
        }
    },
    children: [
        {
            path: '/',
            component: InternalDashboard
        },
        {
            path: 'approvals',
            component: ApprovalDash,
            name:"internal-approvals-dash"
        },
        {
            path: 'search',
            component: Search,
            name:"internal-search"
        },
        {
            path: 'organisations',
            component: {
                render(c)
                {
                    return c('router-view')
                }
            },
            children: [
                {
                    path: 'access',
                    component: OrgAccessTable,
                    name:"org-access-dash"
                },
                {
                    path: 'access/:access_id',
                    component: OrgAccess,
                    name:"org-access"
                },
                {
                    path: ':org_id',
                    component: Organisation,
                    name:"internal-org-detail"
                },
 
            ]
        },
        {
            path: 'proposal',
            component: {
                render(c)
                {
                    return c('router-view')
                }
            },
            children: [
                {
                    path: ':proposal_id',
                    component: {
                        render(c)
                        {
                            return c('router-view')
                        }
                    },
                    children: [
                        {
                            path: '/',
                            component: Proposal,
                            name:"internal-proposal"
                        },
                        {
                            path: 'referral/:referral_id',
                            component: Referral,
                            name:"internal-referral"
                        },
                    ]
                },
 
            ]
        },
        /*{
            path: 'proposal',
            component: Proposal,
            name:"new_proposal"
        }*/
    ]
}
