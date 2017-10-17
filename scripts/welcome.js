// Description
//   Welcomes new users to UQCS Slack and check for member milestones

var MEMBER_MILESTONE = 50;
var MESSAGE_PAUSE = 2500;
var WELCOME_MESSAGES = [
    "Hey there! Welcome to the UQCS slack!",
    "This is the first time I've seen you, so you're probably new here",
    "I'm UQCSbot, your friendly (open source) robot helper",
    "We've got a bunch of generic channels (e.g. #banter, #games, #projects) along with many subject-specific ones",
    "Your friendly admins are @trm, @mitch, @rob, @mb, @csa, @guthers, and @artemis",
    "Type \"help\" here, or \"!help\" anywhere else to find out what I can do!",
    "and again, welcome :)"
];

module.exports = function (robot) {
    robot.enter(function (res) {
        // Make sure we have access to all the clients we need
        if(!robot.adapter.client || !robot.adapter.client.rtm || !robot.adapter.client.web) {
            return;
        }

        // Check the user has entered general
        var general = robot.adapter.client.rtm.dataStore.getChannelByName("general").id; 
        if (res.message.room != general) {
            return;
        }
        
        // Welcome them to general and send them a personal welcome
        res.send("Welcome, " + res.message.user.name + "!");
        WELCOME_MESSAGES.forEach((message, i) => setTimeout(() => {
            robot.send({room: res.message.user.id}, message);
        }, i * MESSAGE_PAUSE));

        // Check member count to see if we've hit a member milestone
        robot.adapter.client.web.conversations.members(general).then(result => {
            // Create a list of promises that resolve to each member's status
            var memberPromises = result.members.map(id => {
                return robot.adapter.client.web.users.info(id)
                    .then(user => (user.deleted) ? 0 : 1);
                });

            // Get accurate sum of users, filtering out all who are deleted
            Promise.all(memberPromises)
                .then(statuses => statuses.reduce((a, b) => a + b, 0))
                .then(memberCount => {
                    // If we're not at a member milestone, don't bother celebrating!
                    if (memberCount % MEMBER_MILESTONE != 0) {
                        return;
                    }

                    res.send(":tada: " + memberCount + " members! :tada:");
                });
        });
    });
};
